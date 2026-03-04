#!/usr/bin/env python3
"""
Write-Through vs Write-Back Cache Policy Comparison
NACHO Framework — Checkpoint Report Visualization
"""

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# =============================================================================
# DATA — sourced from benchmark logs (512B cache, 2 lines, Os, no power fail)
# Populate write_through values once the nohup job finishes
# =============================================================================

benchmarks = ['adpcm', 'aes', 'coremark', 'crc', 'dijkstra', 'picojpeg', 'quicksort', 'sha', 'towers']

# Write-Back (nacho_pw) — CONFIRMED from benchmarks/logs/
write_back = {
    'nvm_writes':        [1940824, 516716, 145308, 2776,    11138168, 17092024, 187528,  3674968, 5233516],
    'cycles':            [54656360, 12938262, 3486166, 41548, 122623512, 69291132, 1726969, 33933884, 15964910],
    'checkpoint_cycles': [3409126, 999554, 273610, 5210,   23929720, 37134562, 364194,  6680108, 10867316],
    'checkpoints':       [2737,    701,    201,    3,       33293,    53404,    277,     3617,    12870],
}

# Write-Through — confirmed from /tmp/benchmark-logs/*-512-2-0-0Os-final
# Order: adpcm, aes, coremark, crc, dijkstra, picojpeg, quicksort, sha, towers
write_through = {
    'nvm_writes':        [93665104, 239237328, 16074112, 180336, 29770400, 345199824, 6714864, 171042032, 44577264],
    'cycles':            [266179414, 552240162, 39899831, 443768, 171501253, 812293980, 16558970, 413481244, 104715857],
    'checkpoint_cycles': [210746484, 538283988, 36166752, 405756, 66983400, 776699604, 15108444, 384844572, 100298844],
    'checkpoints':       [344357, 879549, 59096, 663, 109450, 1269117, 24687, 628831, 163887],
}

# =============================================================================
# PLOTTING
# =============================================================================

COLORS = {'wb': '#3B82F6', 'wt': '#EF4444'}
BENCH_LABELS = ['adpcm', 'aes', 'coremark', 'crc', 'dijkstra', 'picojpeg', 'quicksort', 'sha', 'towers']

def safe_ratio(wt, wb):
    """Return wt/wb ratio, or None if either is missing."""
    if wt is None or wb is None or wb == 0:
        return None
    return wt / wb

def plot_metric(ax, metric_key, ylabel, title, logy=False):
    x = np.arange(len(benchmarks))
    width = 0.35

    wb_vals = write_back[metric_key]
    wt_vals = write_through[metric_key]

    # Filter to benchmarks with both values available
    has_both = [i for i in range(len(benchmarks)) if wt_vals[i] is not None]
    x_both = np.array([i for i in x if i in has_both])
    x_wb_only = np.array([i for i in x if i not in has_both])

    bars_wb = ax.bar(x - width/2, wb_vals, width, label='Write-Back (NACHO PW)', color=COLORS['wb'], alpha=0.85)

    wt_plot = [wt_vals[i] if wt_vals[i] is not None else 0 for i in range(len(benchmarks))]
    bars_wt = ax.bar(x + width/2, wt_plot, width, label='Write-Through (Proposed)', color=COLORS['wt'], alpha=0.85)

    # Mark pending benchmarks
    for i in x_wb_only:
        ax.text(i + width/2, wb_vals[i] * 0.5, 'TBD', ha='center', va='center',
                fontsize=7, color='gray', style='italic')

    # Add ratio labels above write-through bars where data exists
    for i in has_both:
        ratio = safe_ratio(wt_vals[i], wb_vals[i])
        if ratio:
            ax.text(i + width/2, wt_vals[i] * 1.02,
                    f'{ratio:.1f}x', ha='center', va='bottom', fontsize=8, fontweight='bold', color=COLORS['wt'])

    ax.set_xlabel('Benchmark', fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_title(title, fontsize=13, fontweight='bold', pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(BENCH_LABELS, rotation=30, ha='right', fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda val, _: f'{val:,.0f}'))
    ax.legend(fontsize=9)
    ax.grid(axis='y', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    if logy:
        ax.set_yscale('log')

fig, axes = plt.subplots(1, 3, figsize=(18, 6))
fig.suptitle('Write-Through vs Write-Back Cache Policy Comparison\n(512B Cache, 2-Way, No Power Failures)',
             fontsize=15, fontweight='bold', y=1.02)

plot_metric(axes[0], 'nvm_writes',        'NVM Writes',          'NVM Write Count\n(lower is better)')
plot_metric(axes[1], 'cycles',            'Total Cycles',        'Execution Cycles\n(lower is better)')
plot_metric(axes[2], 'checkpoint_cycles', 'Checkpoint Cycles',   'Checkpoint Overhead Cycles\n(lower is better)')

plt.tight_layout()
plt.savefig('results/write_through_comparison.png', dpi=150, bbox_inches='tight')
plt.savefig('results/write_through_comparison.pdf', bbox_inches='tight')
print("Saved: results/write_through_comparison.png")
print("Saved: results/write_through_comparison.pdf")
plt.show()

# =============================================================================
# PRINT COMPARISON TABLE
# =============================================================================
print("\n" + "="*90)
print(f"{'Benchmark':<12} {'WB NVM Writes':>14} {'WT NVM Writes':>14} {'NVM Ovhd':>10} {'WB Cycles':>14} {'WT Cycles':>14} {'Slowdown':>10}")
print("="*90)
for i, bench in enumerate(benchmarks):
    wb_nvm = write_back['nvm_writes'][i]
    wt_nvm = write_through['nvm_writes'][i]
    wb_cyc = write_back['cycles'][i]
    wt_cyc = write_through['cycles'][i]
    nvm_r = f"{wt_nvm/wb_nvm:.1f}x" if wt_nvm else "TBD"
    cyc_r = f"{wt_cyc/wb_cyc:.1f}x" if wt_cyc else "TBD"
    wt_nvm_s = f"{wt_nvm:,}" if wt_nvm else "TBD"
    wt_cyc_s = f"{wt_cyc:,}" if wt_cyc else "TBD"
    print(f"{bench:<12} {wb_nvm:>14,} {wt_nvm_s:>14} {nvm_r:>10} {wb_cyc:>14,} {wt_cyc_s:>14} {cyc_r:>10}")
print("="*90)
