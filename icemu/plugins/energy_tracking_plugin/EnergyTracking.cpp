/**
 * ICEmu Energy Tracking Plugin — Phase 2 (NVM classification experiment)
 *
 * Phase 2 adds NVM address-range classification.
 * Pass -a energy-nvm-base-address=0x80000000 to enable NVM detection.
 *
 * This is an experiment to test whether ICEmu's memory hook fires for
 * cache-plugin-internal NVM writes (cacheNVMwrite calls), or only for
 * CPU-level instruction-driven accesses.
 *
 * If the hook DOES see NVM writes: write-through will show far more
 * nvm_write_bytes than write-back, proving the hook can differentiate.
 * If NOT: nvm_write_bytes will be 0 for both, confirming Phase 1 limitation.
 *
 * Usage:
 *   icemu -p energy_tracking_plugin.so \
 *         -a energy-nvm-base-address=0x80000000 \
 *         -a energy-log-file=<name> program.elf
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

class EnergyCost {
  public:
    static constexpr double CPU_INSTRUCTION_ENERGY = 0.5;
    static constexpr double CACHE_READ_ENERGY  = 0.2;
    static constexpr double CACHE_WRITE_ENERGY = 0.3;
    static constexpr double NVM_READ_ENERGY    = 2.0;
    static constexpr double NVM_WRITE_ENERGY   = 5.0;

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

struct EnergyStats {
    double total_energy_pj        = 0.0;
    double cpu_energy_pj          = 0.0;
    double cache_read_energy_pj   = 0.0;
    double cache_write_energy_pj  = 0.0;
    double nvm_read_energy_pj     = 0.0;
    double nvm_write_energy_pj    = 0.0;

    uint64_t instruction_count  = 0;
    uint64_t cache_read_bytes   = 0;
    uint64_t cache_write_bytes  = 0;
    uint64_t nvm_read_bytes     = 0;
    uint64_t nvm_write_bytes    = 0;

    // Phase 2 experiment: raw access count to NVM region (regardless of i/d)
    uint64_t nvm_region_reads   = 0;
    uint64_t nvm_region_writes  = 0;
    uint64_t nvm_region_read_bytes  = 0;
    uint64_t nvm_region_write_bytes = 0;

    uint64_t current_cycle = 0;
    vector<double>   energy_snapshots;
    vector<uint64_t> snapshot_cycles;
};

// =============================================================================
// Hook Classes
// =============================================================================

class EnergyInstructionTracker : public HookCode {
  private:
    mutable RiscvE21Pipeline Pipeline;

    static int NoMemCost(cs_insn *insn) { (void)insn; return 0; }

  public:
    EnergyStats stats;
    EnergyCost  energy_cost;

    EnergyInstructionTracker(Emulator &emu)
        : HookCode(emu, "energy_instruction_tracker"),
          Pipeline(emu, &NoMemCost, &NoMemCost) {
        Pipeline.setVerifyJumpDestinationGuess(false);
        Pipeline.setVerifyNextInstructionGuess(false);
        parseEnergyMultipliers();
    }

    ~EnergyInstructionTracker() {}

    void run(hook_arg *arg) {
        Pipeline.add(arg->address, arg->size);
        double insn_energy = energy_cost.calculateInstructionEnergy();
        stats.cpu_energy_pj   += insn_energy;
        stats.total_energy_pj += insn_energy;
        stats.instruction_count++;
        stats.current_cycle = Pipeline.getTotalCycles();
    }

    uint64_t getCycleCount() const { return Pipeline.getTotalCycles(); }

  private:
    void parseEnergyMultipliers() {
        auto arg_cpu = PluginArgumentParsing::GetArguments(getEmulator(), "energy-cpu-multiplier=");
        if (arg_cpu.size()) energy_cost.cpu_multiplier = stod(arg_cpu[0]);

        auto arg_cache = PluginArgumentParsing::GetArguments(getEmulator(), "energy-cache-multiplier=");
        if (arg_cache.size()) energy_cost.cache_multiplier = stod(arg_cache[0]);

        auto arg_nvm = PluginArgumentParsing::GetArguments(getEmulator(), "energy-nvm-multiplier=");
        if (arg_nvm.size()) energy_cost.nvm_multiplier = stod(arg_nvm[0]);
    }
};

class EnergyMemoryTracker : public HookMemory {
  private:
    string printLeader() { return "[energy_tracking]"; }

    string   log_file;
    uint64_t snapshot_interval;
    EnergyCost energy_cost;

    EnergyInstructionTracker &instruction_tracker;

    // Phase 2: NVM address range classification
    bool     nvm_classification_enabled = false;
    uint64_t nvm_base_address = 0;
    uint64_t nvm_size         = 0;  // 0 = entire address space from base

  public:
    EnergyMemoryTracker(Emulator &emu, EnergyInstructionTracker &tracker)
        : HookMemory(emu, "energy_memory_tracker"),
          instruction_tracker(tracker),
          log_file("energy_tracking_log"),
          snapshot_interval(0) {

        auto arg_log = PluginArgumentParsing::GetArguments(getEmulator(), "energy-log-file=");
        if (arg_log.size()) log_file = arg_log[0];

        auto arg_snap = PluginArgumentParsing::GetArguments(getEmulator(), "energy-snapshot-interval=");
        if (arg_snap.size()) snapshot_interval = stoull(arg_snap[0]);

        // Phase 2: parse NVM base address for classification experiment
        auto arg_nvm_base = PluginArgumentParsing::GetArguments(getEmulator(), "energy-nvm-base-address=");
        if (arg_nvm_base.size()) {
            nvm_base_address = stoull(arg_nvm_base[0], nullptr, 16);
            nvm_classification_enabled = true;
            cout << printLeader() << " [Phase 2] NVM classification enabled: base=0x"
                 << hex << nvm_base_address << dec << endl;
        }

        auto arg_nvm_size = PluginArgumentParsing::GetArguments(getEmulator(), "energy-nvm-size=");
        if (arg_nvm_size.size()) nvm_size = stoull(arg_nvm_size[0], nullptr, 16);

        energy_cost = tracker.energy_cost;

        cout << printLeader() << " using log file: " << log_file << endl;
    }

    ~EnergyMemoryTracker() {
        printFinalStats();
        logFinalStats();
    }

    void run(hook_arg_t *arg) {
        EnergyStats &stats = instruction_tracker.stats;

        // Phase 2: classify access as NVM or cache based on address
        bool is_nvm = false;
        if (nvm_classification_enabled) {
            if (arg->address >= nvm_base_address) {
                if (nvm_size == 0 || arg->address < nvm_base_address + nvm_size) {
                    is_nvm = true;
                    // Raw experiment counts (separate from energy, for analysis)
                    if (arg->mem_type == MEM_READ) {
                        stats.nvm_region_reads++;
                        stats.nvm_region_read_bytes += arg->size;
                    } else {
                        stats.nvm_region_writes++;
                        stats.nvm_region_write_bytes += arg->size;
                    }
                }
            }
        }

        switch(arg->mem_type) {
        case MEM_READ:
            if (is_nvm) {
                double e = energy_cost.calculateNVMReadEnergy(arg->size);
                stats.nvm_read_energy_pj  += e;
                stats.total_energy_pj     += e;
                stats.nvm_read_bytes      += arg->size;
            } else {
                double e = energy_cost.calculateCacheReadEnergy(arg->size);
                stats.cache_read_energy_pj += e;
                stats.total_energy_pj      += e;
                stats.cache_read_bytes     += arg->size;
            }
            break;

        case MEM_WRITE:
            if (is_nvm) {
                double e = energy_cost.calculateNVMWriteEnergy(arg->size);
                stats.nvm_write_energy_pj += e;
                stats.total_energy_pj     += e;
                stats.nvm_write_bytes     += arg->size;
            } else {
                double e = energy_cost.calculateCacheWriteEnergy(arg->size);
                stats.cache_write_energy_pj += e;
                stats.total_energy_pj       += e;
                stats.cache_write_bytes     += arg->size;
            }
            break;
        }

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
        cout << fixed << setprecision(2);
        cout << "Total Energy:           " << stats.total_energy_pj << " pJ" << endl;

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
        cout << "Operation Counts:" << endl;
        cout << "  Instructions:         " << stats.instruction_count << endl;
        cout << "  Cache Reads:          " << stats.cache_read_bytes << " bytes" << endl;
        cout << "  Cache Writes:         " << stats.cache_write_bytes << " bytes" << endl;
        if (nvm_classification_enabled) {
            cout << "  NVM Reads:            " << stats.nvm_read_bytes << " bytes" << endl;
            cout << "  NVM Writes:           " << stats.nvm_write_bytes << " bytes" << endl;
            cout << "  [Exp] Raw NVM region reads:  " << stats.nvm_region_reads
                 << " ops (" << stats.nvm_region_read_bytes << " bytes)" << endl;
            cout << "  [Exp] Raw NVM region writes: " << stats.nvm_region_writes
                 << " ops (" << stats.nvm_region_write_bytes << " bytes)" << endl;
        }
        cout << "  Total Cycles:         " << instruction_tracker.getCycleCount() << endl;

        uint64_t total_cycles = instruction_tracker.getCycleCount();
        if (total_cycles > 0 && stats.instruction_count > 0) {
            cout << "---------------------------------------------" << endl;
            cout << "Energy per cycle:       " << (stats.total_energy_pj / total_cycles) << " pJ/cycle" << endl;
            cout << "Energy per instruction: " << (stats.total_energy_pj / stats.instruction_count) << " pJ/insn" << endl;
        }
        cout << "=============================================" << endl;
    }

    void logFinalStats() {
        ofstream log(log_file);
        if (!log.is_open()) {
            cout << printLeader() << " ERROR: Failed to open log file: " << log_file << endl;
            return;
        }
        const EnergyStats &stats = instruction_tracker.stats;

        log << fixed << setprecision(6);
        log << "total_energy_pj:"       << stats.total_energy_pj       << endl;
        log << "cpu_energy_pj:"         << stats.cpu_energy_pj         << endl;
        log << "cache_read_energy_pj:"  << stats.cache_read_energy_pj  << endl;
        log << "cache_write_energy_pj:" << stats.cache_write_energy_pj << endl;
        log << "nvm_read_energy_pj:"    << stats.nvm_read_energy_pj    << endl;
        log << "nvm_write_energy_pj:"   << stats.nvm_write_energy_pj   << endl;
        log << "instruction_count:"     << stats.instruction_count     << endl;
        log << "cache_read_bytes:"      << stats.cache_read_bytes       << endl;
        log << "cache_write_bytes:"     << stats.cache_write_bytes      << endl;
        log << "nvm_read_bytes:"        << stats.nvm_read_bytes         << endl;
        log << "nvm_write_bytes:"       << stats.nvm_write_bytes        << endl;
        log << "nvm_region_reads:"      << stats.nvm_region_reads       << endl;
        log << "nvm_region_writes:"     << stats.nvm_region_writes      << endl;
        log << "nvm_region_read_bytes:" << stats.nvm_region_read_bytes  << endl;
        log << "nvm_region_write_bytes:"<< stats.nvm_region_write_bytes << endl;
        log << "total_cycles:"          << instruction_tracker.getCycleCount() << endl;

        uint64_t total_cycles = instruction_tracker.getCycleCount();
        if (total_cycles > 0 && stats.instruction_count > 0) {
            log << "energy_per_cycle_pj:"       << (stats.total_energy_pj / total_cycles) << endl;
            log << "energy_per_instruction_pj:" << (stats.total_energy_pj / stats.instruction_count) << endl;
        }
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

static void registerEnergyTrackingHook(Emulator &emu, HookManager &HM) {
    auto *instruction_tracker = new EnergyInstructionTracker(emu);
    assert(instruction_tracker != nullptr);

    auto *memory_tracker = new EnergyMemoryTracker(emu, *instruction_tracker);
    assert(memory_tracker != nullptr);

    HM.add(instruction_tracker);
    HM.add(memory_tracker);
}

RegisterHook RegisterMyHook(registerEnergyTrackingHook);
