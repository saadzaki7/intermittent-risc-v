#!/usr/bin/env python3
"""
Write-Through vs Write-Back Cache Policy Comparison — v3 (Accurate Evaluation)
NACHO Framework — Checkpoint Report Visualization
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

benchmarks  = ['adpcm', 'aes', 'coremark', 'crc', 'dijkstra', 'picojpeg', 'quicksort', 'sha', 'towers']
bench_labels = ['adpcm', 'aes', 'coremark', 'crc', 'dijkstra', 'picojpeg', 'quicksort', 'sha', 'towers']

# ── Write-Back (NACHO PW) ──
write_back = {
    'cycles':            [54656360,  12938262, 3486166, 41548,    122623512, 69291132, 1726969, 33933884, 15964910],
    'checkpoints':       [2737,       701,      201,     3,         33293,    53404,    277,      3617,     12870],
    'checkpoint_cycles': [3409126,   999554,   273610,  5210,     23929720,  37134562, 364194,  6680108,  10867316],
    'nvm_writes':        [2639030,   1566202,  590411,  5777,     18144596,  22559884, 373036,  6348013,  7593368],
}

# ── Write-Through v3 ──
write_through = {
    'cycles':            [266179414, 552240162, 39899831, 443768, 171501253, 812293980, 16558970, 413481244, 104715857],
    'checkpoints':       [344357,    879549,    59096,    663,    109450,    1269117,   24687,    628831,    163887],
    'checkpoint_cycles': [210746484, 538283988, 36166752, 405756, 66983400,  776699604, 15108444, 384844572, 100298844],
    'nvm_writes':        [93665104,  239237328, 16074112, 180336, 29770400,  345199824, 6714864,  171042032, 44577264]
}

# ── Normalise ──
def norm(wt_list, wb_list):
    return [wt/wb for wt, wb in zip(wt_list, wb_list)]

norm_cycles     = norm(write_through['cycles'], write_back['cycles'])
norm_nvm_writes = norm(write_through['nvm_writes'], write_back['nvm_writes'])

# ── Colors ──
WB_COLOR = '#3B82F6'   # blue
WT_COLOR = '#EF4444'   # red

x     = np.arange(len(benchmarks))
width = 0.38

def save_fig(fig, filename):
    fig.patch.set_facecolor('#0F172A')
    axes = fig.axes
    for ax in axes:
        ax.set_facecolor('#1E293B')
        ax.tick_params(colors='#94A3B8')
        ax.spines['bottom'].set_color('#334155')
        ax.spines['left'].set_color('#334155')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.yaxis.label.set_color('#94A3B8')
        ax.grid(axis='y', alpha=0.15, color='white')
        ax.set_xticks(x)
        ax.set_xticklabels(bench_labels, color='#CBD5E1', fontsize=10)
        ax.legend(fontsize=10, facecolor='#1E293B', labelcolor='white', edgecolor='#334155')

    fig.tight_layout()
    fig.savefig(filename, dpi=150, bbox_inches='tight', facecolor='#0F172A')
    print(f"Saved: {filename}")

# Fig 1: Cycles
fig1, ax1 = plt.subplots(figsize=(11, 5))
ax1.bar(x - width/2, [1.0]*len(benchmarks), width, label='Write-Back (Baseline)', color=WB_COLOR)
ax1.bar(x + width/2, norm_cycles, width, label='Write-Through (Accurate)', color=WT_COLOR)
for i, v in enumerate(norm_cycles):
    ax1.text(i + width/2, max(v+0.02, 0.08), f'{v:.1f}X', ha='center', va='bottom', fontsize=8.5, fontweight='bold', color='#FCA5A5')
ax1.axhline(1.0, color='white', linewidth=0.8, linestyle='--')
ax1.set_ylabel('Normalised Execution Cycles')
ax1.set_title('Write-Through Idempotent Overhead\n(Values > 1.0 indicate performance degradation vs Write-Back)', color='white')
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f'{v:.1f}X'))
ax1.set_ylim(0, max(norm_cycles)*1.15)
save_fig(fig1, 'results/wt_v3_cycles_comparison.png')

# Fig 2: NVM Writes
fig2, ax2 = plt.subplots(figsize=(11, 5))
ax2.bar(x - width/2, [1.0]*len(benchmarks), width, label='Write-Back (Baseline)', color=WB_COLOR)
ax2.bar(x + width/2, norm_nvm_writes, width, label='Write-Through (Accurate)', color=WT_COLOR)
for i, v in enumerate(norm_nvm_writes):
    ax2.text(i + width/2, max(v+0.02, 0.08), f'{v:.1f}X', ha='center', va='bottom', fontsize=8.5, fontweight='bold', color='#FCA5A5')
ax2.axhline(1.0, color='white', linewidth=0.8, linestyle='--')
ax2.set_ylabel('Normalised NVM Writes')
ax2.set_title('NVM Wear-Out Degradation\n(Due to constant flush-throughs and emergency checkpoints)', color='white')
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f'{v:.1f}X'))
ax2.set_ylim(0, max(norm_nvm_writes)*1.15)
save_fig(fig2, 'results/wt_v3_nvm_writes.png')

print("\n=== Final Accurate Summary Table ===")
print(f"{'Benchmark':<12} {'WB Cycles':>14} {'WTv3 Cycles':>14} {'Definitive Ratio':>18}")
print("─"*70)
for i, b in enumerate(benchmarks):
    ratio = write_through['cycles'][i] / write_back['cycles'][i]
    print(f"{b:<12} {write_back['cycles'][i]:>14,} {write_through['cycles'][i]:>14,} "
          f"{ratio:>14.2f}X slower")

print("\n=== Final Wear-Out Summary Table ===")
print(f"{'Benchmark':<12} {'WB NVM Writes':>14} {'WT NVM Writes':>14} {'Degradation':>16}")
print("─"*70)
for i, b in enumerate(benchmarks):
    ratio = write_through['nvm_writes'][i] / write_back['nvm_writes'][i]
    print(f"{b:<12} {write_back['nvm_writes'][i]:>14,} {write_through['nvm_writes'][i]:>14,} {ratio:>11.1f}X")
