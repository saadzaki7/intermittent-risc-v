#!/bin/bash

# Check input arguments
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <benchmark> <optimization_level> <system>"
    echo "Example: $0 aes O0 nacho"
    echo "Systems: nacho, nacho-write-through, replaycache"
    echo "Important: Please ensure that ICEmu plugins and LLVM toolchain are compiled"
    exit 1
fi

set -e
export MAKEFLAGS="$MAKEFLAGS -j$(nproc)"

# Ensure the LLVM toolchain is compiled (incremental)
make llvm nodownload=1

# Ensure ICEmu plugins are built (incremental)
# Assuming ICEmu itself does not need recompilation
cmake --build icemu/plugins/build

# Ensure benchmarks are built (incremental)
make -C benchmarks clean
make -C benchmarks clean build

# Assign command-line arguments
bench=$1
opt_lvl=$2
system=$3

# Common parameters but we can make it as args if needed
cache=512
lines=2
on_duration=0

# Log directory
LOGDIR="/tmp/benchmark-logs"
mkdir -p $LOGDIR

# Select the appropriate system and plugin
if [ "$system" == "nacho" ]; then
    plugin="custom_cache_plugin.so"
    log_file="$LOGDIR/uninstrumented-$bench"
    extra_args="-a enable-pw-bit=1 -a enable-stack-tracking=2 -a enable-write-through=0"
elif [ "$system" == "nacho-write-through" ]; then
    plugin="custom_cache_plugin.so"
    log_file="$LOGDIR/write-through-$bench"
    extra_args="-a enable-pw-bit=1 -a enable-stack-tracking=2 -a enable-write-through=1"
elif [ "$system" == "replaycache" ]; then
    plugin="replay_cache_plugin.so"
    log_file="$LOGDIR/replay-cache-$bench"
    extra_args="-a writeback-queue-size=8 -a writeback-parallelism=1 -a on-duration=$on_duration"
else
    echo "Error: Invalid system '$system'. Choose either 'nacho', 'nacho-write-through', or 'replaycache'."
    exit 1
fi

# Run the benchmark (co-loading the energy plugin for energy accounting)
energy_log_file="$LOGDIR/energy-$system-$bench"

exec run-elf \
    -p $plugin \
    -p energy_tracking_plugin.so \
    -a hash-method=0 \
    -a cache-size=$cache \
    -a cache-lines=$lines \
    -a custom-cache-log-file=$log_file \
    -a energy-log-file=$energy_log_file \
    -a opt-level=$opt_lvl \
    $extra_args \
    ./benchmarks/$bench/build-replay-cache-$opt_lvl/$bench.elf
