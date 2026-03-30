/**
 * ICEmu Energy Tracking Plugin
 *
 * A plugin that tracks energy consumption during ICEmu emulation.
 *
 * This plugin provides energy modeling for:
 * - CPU instruction execution
 * - Cache memory reads
 * - Cache memory writes
 * - Optional: NVM operations
 *
 * Energy values are hardcoded constants (in picojoules) but can be
 * scaled using command-line multipliers for sensitivity analysis.
 *
 * Usage:
 *   icemu -p energy_tracking_plugin.so [options] program.elf
 *
 * Options:
 *   --energy-log-file=<name>           Output log file name
 *   --energy-snapshot-interval=<n>     Take snapshots every n cycles
 *   --energy-cpu-multiplier=<f>        Scale CPU energy by factor f
 *   --energy-cache-multiplier=<f>      Scale cache energy by factor f
 *   --energy-nvm-multiplier=<f>        Scale NVM energy by factor f
 */

#include <iostream>
#include <fstream>
#include <iomanip>
#include <vector>
#include <cmath>

#include "capstone/capstone.h"

#include "icemu/emu/types.h"
#include "icemu/emu/Emulator.h"
#include "icemu/hooks/HookCode.h"
#include "icemu/hooks/HookMemory.h"
#include "icemu/hooks/HookManager.h"
#include "icemu/hooks/RegisterHook.h"

#include "Riscv32E21Pipeline.hpp"
#include "PluginArgumentParsing.h"

using namespace std;
using namespace icemu;

// =============================================================================
// Energy Model and Statistics
// =============================================================================

/**
 * Energy cost calculator with hardcoded energy values.
 * All energy values are in picojoules (pJ).
 *
 * Default values are based on typical embedded system characteristics:
 * - CPU instruction: ~0.5 pJ (simple RISC-V ALU operation)
 * - Cache read: ~0.2 pJ per byte (SRAM read)
 * - Cache write: ~0.3 pJ per byte (SRAM write, slightly higher than read)
 * - NVM read: ~2.0 pJ per byte (Flash/FRAM, 10x cache)
 * - NVM write: ~5.0 pJ per byte (Flash/FRAM, high write cost)
 *
 * These values can be scaled using multipliers for sensitivity analysis.
 */
class EnergyCost {
  public:
    // Base energy costs in picojoules (pJ)
    static constexpr double CPU_INSTRUCTION_ENERGY = 0.5;
    static constexpr double CACHE_READ_ENERGY = 0.2;
    static constexpr double CACHE_WRITE_ENERGY = 0.3;
    static constexpr double NVM_READ_ENERGY = 2.0;
    static constexpr double NVM_WRITE_ENERGY = 5.0;

    // Configurable multipliers for sensitivity analysis
    double cpu_multiplier;
    double cache_multiplier;
    double nvm_multiplier;

    EnergyCost() : cpu_multiplier(1.0), cache_multiplier(1.0), nvm_multiplier(1.0) {}

    double calculateInstructionEnergy() const {
        return CPU_INSTRUCTION_ENERGY * cpu_multiplier;
    }

    double calculateCacheReadEnergy(uint64_t bytes) const {
        return CACHE_READ_ENERGY * bytes * cache_multiplier;
    }

    double calculateCacheWriteEnergy(uint64_t bytes) const {
        return CACHE_WRITE_ENERGY * bytes * cache_multiplier;
    }

    double calculateNVMReadEnergy(uint64_t bytes) const {
        return NVM_READ_ENERGY * bytes * nvm_multiplier;
    }

    double calculateNVMWriteEnergy(uint64_t bytes) const {
        return NVM_WRITE_ENERGY * bytes * nvm_multiplier;
    }
};

/**
 * Statistics structure for tracking energy consumption.
 */
struct EnergyStats {
    // Total energy consumption
    double total_energy_pj;

    // Component breakdown
    double cpu_energy_pj;
    double cache_read_energy_pj;
    double cache_write_energy_pj;
    double nvm_read_energy_pj;
    double nvm_write_energy_pj;

    // Operation counts (for verification/debugging)
    uint64_t instruction_count;
    uint64_t cache_read_bytes;
    uint64_t cache_write_bytes;
    uint64_t nvm_read_bytes;
    uint64_t nvm_write_bytes;

    // Time-based tracking
    uint64_t current_cycle;
    vector<double> energy_snapshots;
    vector<uint64_t> snapshot_cycles;

    EnergyStats() : total_energy_pj(0.0), cpu_energy_pj(0.0),
                    cache_read_energy_pj(0.0), cache_write_energy_pj(0.0),
                    nvm_read_energy_pj(0.0), nvm_write_energy_pj(0.0),
                    instruction_count(0), cache_read_bytes(0),
                    cache_write_bytes(0), nvm_read_bytes(0),
                    nvm_write_bytes(0), current_cycle(0) {}
};

// =============================================================================
// Hook Classes
// =============================================================================

/**
 * HookCode implementation for tracking instruction execution energy.
 */
class EnergyInstructionTracker : public HookCode {
  private:
    mutable RiscvE21Pipeline Pipeline;

    static int NoMemCost(cs_insn *insn) {
        (void)insn;
        return 0;
    }

  public:
    EnergyStats stats;
    EnergyCost energy_cost;

    EnergyInstructionTracker(Emulator &emu): HookCode(emu, "energy_instruction_tracker"), Pipeline(emu, &NoMemCost, &NoMemCost) {

        Pipeline.setVerifyJumpDestinationGuess(false);
        Pipeline.setVerifyNextInstructionGuess(false);

        // Parse energy multipliers from command-line
        parseEnergyMultipliers();
    }

    ~EnergyInstructionTracker() {}

    void run(hook_arg *arg) {
        // Track instruction execution in pipeline
        Pipeline.add(arg->address, arg->size);

        // Calculate and add instruction energy
        double insn_energy = energy_cost.calculateInstructionEnergy();
        stats.cpu_energy_pj += insn_energy;
        stats.total_energy_pj += insn_energy;
        stats.instruction_count++;

        // Update current cycle
        stats.current_cycle = Pipeline.getTotalCycles();
    }

    uint64_t getCycleCount() const {
        return Pipeline.getTotalCycles();
    }

 private:
    void parseEnergyMultipliers() {
        auto arg_cpu = PluginArgumentParsing::GetArguments(
            getEmulator(), "energy-cpu-multiplier=");
        if (arg_cpu.size()) energy_cost.cpu_multiplier = stod(arg_cpu[0]);

        auto arg_cache = PluginArgumentParsing::GetArguments(
            getEmulator(), "energy-cache-multiplier=");
        if (arg_cache.size()) energy_cost.cache_multiplier = stod(arg_cache[0]);

        auto arg_nvm = PluginArgumentParsing::GetArguments(getEmulator(), "energy-nvm-multiplier=");
        if (arg_nvm.size())
            energy_cost.nvm_multiplier = stod(arg_nvm[0]);
        }
    };

    /**
    * HookMemory implementation for tracking memory operation energy.
    */
    class EnergyMemoryTracker : public HookMemory {
    private:
    string printLeader() {
        return "[energy_tracking]";
    }

    // Configuration
    string log_file;
    uint64_t snapshot_interval;

    // Energy cost calculator (shared config with instruction tracker)
    EnergyCost energy_cost;

    // Reference to instruction tracker for shared stats
    EnergyInstructionTracker &instruction_tracker;

    public:
    EnergyMemoryTracker(Emulator &emu, EnergyInstructionTracker &tracker)
        : HookMemory(emu, "energy_memory_tracker"),
            instruction_tracker(tracker),
            log_file("energy_tracking_log"),
            snapshot_interval(0) {

        // Parse log file argument
        auto arg_log_file = PluginArgumentParsing::GetArguments(
            getEmulator(), "energy-log-file=");
        if (arg_log_file.size()) log_file = arg_log_file[0];

        // Parse snapshot interval
        auto arg_snapshot = PluginArgumentParsing::GetArguments(
            getEmulator(), "energy-snapshot-interval=");
        if (arg_snapshot.size()) snapshot_interval = stoull(arg_snapshot[0]);

        // Copy energy multipliers from instruction tracker
        energy_cost = tracker.energy_cost;

        cout << printLeader() << " using log file: " << log_file << endl;
        if (snapshot_interval > 0) {
            cout << printLeader() << " energy snapshots every " << snapshot_interval << " cycles" << endl;
        }
    }

    ~EnergyMemoryTracker() {
        // Write final statistics to console and log file
        printFinalStats();
        logFinalStats();
    }

    void run(hook_arg_t *arg) {
        EnergyStats &stats = instruction_tracker.stats;

        // Phase 1: Assume all memory is cache
        // Phase 2 would add NVM classification here
        switch(arg->mem_type) {
        case MEM_READ:
            {
                double read_energy = energy_cost.calculateCacheReadEnergy(arg->size);
                stats.cache_read_energy_pj += read_energy;
                stats.total_energy_pj += read_energy;
                stats.cache_read_bytes += arg->size;
            }
            break;

        case MEM_WRITE:
            {
                double write_energy = energy_cost.calculateCacheWriteEnergy(arg->size);
                stats.cache_write_energy_pj += write_energy;
                stats.total_energy_pj += write_energy;
                stats.cache_write_bytes += arg->size;
            }
            break;
        }

        // Optional: Take periodic snapshots
        if (snapshot_interval > 0) {
            uint64_t current_cycle = instruction_tracker.getCycleCount();
            if (stats.snapshot_cycles.empty() ||
                current_cycle - stats.snapshot_cycles.back() >= snapshot_interval) {
                stats.energy_snapshots.push_back(stats.total_energy_pj);
                stats.snapshot_cycles.push_back(current_cycle);
            }
        }
    }

    private:
    void printFinalStats() {
        const EnergyStats &stats = instruction_tracker.stats;

        cout << "\n" << printLeader() << " Energy Statistics:" << endl;
        cout << "=============================================" << endl;

        // Total energy
        cout << fixed << setprecision(2);
        cout << "Total Energy:           " << stats.total_energy_pj << " pJ" << endl;

        // Component breakdown with percentages
        if (stats.total_energy_pj > 0) {
            cout << "  CPU Instructions:     " << stats.cpu_energy_pj << " pJ ("
                << (stats.cpu_energy_pj / stats.total_energy_pj * 100.0) << "%)" << endl;
            cout << "  Cache Reads:          " << stats.cache_read_energy_pj << " pJ ("
                << (stats.cache_read_energy_pj / stats.total_energy_pj * 100.0) << "%)" << endl;
            cout << "  Cache Writes:         " << stats.cache_write_energy_pj << " pJ ("
                << (stats.cache_write_energy_pj / stats.total_energy_pj * 100.0) << "%)" << endl;

            if (stats.nvm_read_energy_pj > 0 || stats.nvm_write_energy_pj > 0) {
                cout << "  NVM Reads:            " << stats.nvm_read_energy_pj << " pJ ("
                    << (stats.nvm_read_energy_pj / stats.total_energy_pj * 100.0) << "%)" << endl;
                cout << "  NVM Writes:           " << stats.nvm_write_energy_pj << " pJ ("
                    << (stats.nvm_write_energy_pj / stats.total_energy_pj * 100.0) << "%)" << endl;
            }
        }

        cout << "---------------------------------------------" << endl;

        // Operation counts
        cout << "Operation Counts:" << endl;
        cout << "  Instructions:         " << stats.instruction_count << endl;
        cout << "  Cache Reads:          " << stats.cache_read_bytes << " bytes" << endl;
        cout << "  Cache Writes:         " << stats.cache_write_bytes << " bytes" << endl;
        if (stats.nvm_read_bytes > 0 || stats.nvm_write_bytes > 0) {
            cout << "  NVM Reads:            " << stats.nvm_read_bytes << " bytes" << endl;
            cout << "  NVM Writes:           " << stats.nvm_write_bytes << " bytes" << endl;
        }
        cout << "  Total Cycles:         " << instruction_tracker.getCycleCount() << endl;

        cout << "---------------------------------------------" << endl;

        // Derived metrics
        uint64_t total_cycles = instruction_tracker.getCycleCount();
        if (total_cycles > 0 && stats.instruction_count > 0) {
        cout << "Energy per cycle:       "
            << (stats.total_energy_pj / total_cycles) << " pJ/cycle" << endl;
        cout << "Energy per instruction: "
            << (stats.total_energy_pj / stats.instruction_count) << " pJ/insn" << endl;
        }

        cout << "=============================================" << endl;
    }

    void logFinalStats() {
        ofstream log(log_file);
        if (!log.is_open()) {
        cout << printLeader() << " ERROR: Failed to open log file: "
            << log_file << endl;
        return;
        }

        const EnergyStats &stats = instruction_tracker.stats;

        // Write summary statistics
        log << fixed << setprecision(6);
        log << "total_energy_pj:" << stats.total_energy_pj << endl;
        log << "cpu_energy_pj:" << stats.cpu_energy_pj << endl;
        log << "cache_read_energy_pj:" << stats.cache_read_energy_pj << endl;
        log << "cache_write_energy_pj:" << stats.cache_write_energy_pj << endl;
        log << "nvm_read_energy_pj:" << stats.nvm_read_energy_pj << endl;
        log << "nvm_write_energy_pj:" << stats.nvm_write_energy_pj << endl;
        log << "instruction_count:" << stats.instruction_count << endl;
        log << "cache_read_bytes:" << stats.cache_read_bytes << endl;
        log << "cache_write_bytes:" << stats.cache_write_bytes << endl;
        log << "nvm_read_bytes:" << stats.nvm_read_bytes << endl;
        log << "nvm_write_bytes:" << stats.nvm_write_bytes << endl;
        log << "total_cycles:" << instruction_tracker.getCycleCount() << endl;

        // Derived metrics
        uint64_t total_cycles = instruction_tracker.getCycleCount();
        if (total_cycles > 0 && stats.instruction_count > 0) {
            log << "energy_per_cycle_pj:" << (stats.total_energy_pj / total_cycles) << endl;
            log << "energy_per_instruction_pj:" << (stats.total_energy_pj / stats.instruction_count) << endl;
        }

        // Write periodic snapshots if enabled
        if (!stats.energy_snapshots.empty()) {
            log << "\n# Energy Snapshots (cycle, energy_pj)" << endl;
            for (size_t i = 0; i < stats.energy_snapshots.size(); i++) {
                log << stats.snapshot_cycles[i] << "," << stats.energy_snapshots[i] << endl;
            }
        }

        log.close();
        cout << printLeader() << " Logged statistics to: " << log_file << endl;
    }
};

// =============================================================================
// Plugin Registration
// =============================================================================

/**
 * Function that registers the hooks with ICEmu.
 * Called by ICEmu when loading the plugin.
 */
static void registerEnergyTrackingHook(Emulator &emu, HookManager &HM) {
    auto *instruction_tracker = new EnergyInstructionTracker(emu);
    assert(instruction_tracker != nullptr);

    auto *memory_tracker = new EnergyMemoryTracker(emu, *instruction_tracker);
    assert(memory_tracker != nullptr);

    // Add instruction tracker first as memory tracker depends on it
    HM.add(instruction_tracker);
    HM.add(memory_tracker);
}

/**
 * Global RegisterHook object.
 * MUST BE NAMED "RegisterMyHook" for ICEmu to find it.
 * MUST BE global scope.
 */
RegisterHook RegisterMyHook(registerEnergyTrackingHook);
