#!/usr/bin/env python3
"""
Write-Through vs Write-Back Cache Policy Comparison — v2 (Fixed Implementation)
NACHO Framework — Checkpoint Report Visualization
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

benchmarks  = ['adpcm', 'aes', 'coremark', 'crc', 'dijkstra', 'picojpeg', 'quicksort', 'sha', 'towers']
bench_labels = ['adpcm', 'aes', 'coremark', 'crc', 'dijkstra', 'picojpeg', 'quicksort', 'sha', 'towers']

# ── Write-Back (NACHO PW) ── confirmed from benchmarks/logs/
write_back = {
    'cycles':            [54656360,  12938262, 3486166, 41548,    122623512, 69291132, 1726969, 33933884, 15964910],
    'checkpoints':       [2737,       701,      201,     3,         33293,    53404,    277,      3617,     12870],
    'checkpoint_cycles': [3409126,   999554,   273610,  5210,     23929720,  37134562, 364194,  6680108,  10867316],
    'nvm_writes_total':  [2639030,   1566202,  590411,  5777,     18144596, 22559884, 373036,   6348013,  7593368],
}

# ── Write-Through v2 (Fixed: no unnecessary WAR checkpoints) ──
# nvm_writes_total estimated as nvm_writes_no_cache + cache_write
# (every cache write = 1 NVM write in write-through)
write_through_v2 = {
    'cycles':            [55432930, 13956174, 3733079, 38012,   104517853, 35594376, 1450526, 28636672, 4417013],
    'checkpoints':       [0,        0,        0,       0,        0,         0,        0,        0,       0],
    'checkpoint_cycles': [0,        0,        0,       0,        0,         0,        0,        0,       0],
    'nvm_writes_total':  [2398364,  2148564, 986856,   6142,    31760652,  12419992, 510852,  5985421,  4719172],
}

# ── Normalise to write-back ──
def norm(wt_list, wb_list):
    return [wt/wb for wt, wb in zip(wt_list, wb_list)]

norm_cycles = norm(write_through_v2['cycles'], write_back['cycles'])
norm_ckps   = norm([c+1 for c in write_through_v2['checkpoints']],
                   [c+1 for c in write_back['checkpoints']])

# ── Colors ──
WB_COLOR = '#3B82F6'   # blue
WT_COLOR = '#F97316'   # orange

x     = np.arange(len(benchmarks))
width = 0.38

# ═══════════════════════════════════════════════════════════════
# Figure 1 — Normalised execution cycles
# ═══════════════════════════════════════════════════════════════
fig1, ax1 = plt.subplots(figsize=(11, 5))
fig1.patch.set_facecolor('#0F172A')
ax1.set_facecolor('#1E293B')

bars_wb = ax1.bar(x - width/2, [1.0]*len(benchmarks), width,
                  label='Write-Back (NACHO baseline)', color=WB_COLOR, alpha=0.88)
bars_wt = ax1.bar(x + width/2, norm_cycles, width,
                  label='Write-Through (this work)', color=WT_COLOR, alpha=0.88)

# Annotate WT bars with × vs baseline
for i, v in enumerate(norm_cycles):
    color = '#4ADE80' if v < 1.0 else '#FCA5A5'
    label = f'{v:.2f}×'
    ax1.text(i + width/2, max(v+0.02, 0.08), label,
             ha='center', va='bottom', fontsize=8.5, fontweight='bold', color=color)

ax1.axhline(1.0, color='white', linewidth=0.8, linestyle='--', alpha=0.4)
ax1.set_xticks(x)
ax1.set_xticklabels(bench_labels, color='#CBD5E1', fontsize=10)
ax1.set_ylabel('Normalised Execution Cycles\n(relative to Write-Back = 1.0)',
               color='#CBD5E1', fontsize=11)
ax1.set_title('Write-Through vs Write-Back: Execution Overhead\n'
              '(values < 1.0 mean write-through is faster)',
              color='white', fontsize=13, fontweight='bold', pad=12)
ax1.tick_params(colors='#94A3B8')
ax1.spines['bottom'].set_color('#334155')
ax1.spines['left'].set_color('#334155')
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.legend(fontsize=10, facecolor='#1E293B', labelcolor='white',
           edgecolor='#334155')
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f'{v:.1f}×'))
ax1.set_ylim(0, max(norm_cycles)*1.22)
ax1.grid(axis='y', alpha=0.15, color='white')
ax1.yaxis.label.set_color('#94A3B8')

plt.tight_layout()
plt.savefig('results/wt_cycles_comparison.png', dpi=150, bbox_inches='tight',
            facecolor='#0F172A')
print("Saved: results/wt_cycles_comparison.png")

# ═══════════════════════════════════════════════════════════════
# Figure 2 — Checkpoint count: absolute
# ═══════════════════════════════════════════════════════════════
fig2, ax2 = plt.subplots(figsize=(11, 5))
fig2.patch.set_facecolor('#0F172A')
ax2.set_facecolor('#1E293B')

ax2.bar(x - width/2, write_back['checkpoints'], width,
        label='Write-Back (NACHO baseline)', color=WB_COLOR, alpha=0.88)
ax2.bar(x + width/2, write_through_v2['checkpoints'], width,
        label='Write-Through (this work)', color=WT_COLOR, alpha=0.88)

# Annotate WB bars with raw counts
for i, v in enumerate(write_back['checkpoints']):
    ax2.text(i - width/2, v * 1.02, f'{v:,}',
             ha='center', va='bottom', fontsize=7.5, color='#93C5FD')
# All WT are 0
for i in x:
    ax2.text(i + width/2, write_back['checkpoints'][i] * 0.05 + 200,
             '0', ha='center', va='bottom', fontsize=9,
             fontweight='bold', color='#4ADE80')

ax2.set_xticks(x)
ax2.set_xticklabels(bench_labels, color='#CBD5E1', fontsize=10)
ax2.set_ylabel('WAR Checkpoint Count', color='#CBD5E1', fontsize=11)
ax2.set_title('WAR Checkpoints Eliminated by Write-Through\n'
              '(write-through keeps NVM always consistent — no checkpoints needed)',
              color='white', fontsize=13, fontweight='bold', pad=12)
ax2.tick_params(colors='#94A3B8')
ax2.spines['bottom'].set_color('#334155')
ax2.spines['left'].set_color('#334155')
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.legend(fontsize=10, facecolor='#1E293B', labelcolor='white',
           edgecolor='#334155')
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f'{int(v):,}'))
ax2.grid(axis='y', alpha=0.15, color='white')
ax2.yaxis.label.set_color('#94A3B8')

plt.tight_layout()
plt.savefig('results/wt_checkpoints_comparison.png', dpi=150, bbox_inches='tight',
            facecolor='#0F172A')
print("Saved: results/wt_checkpoints_comparison.png")

# ═══════════════════════════════════════════════════════════════
# Figure 3 — Checkpoint overhead cycles
# ═══════════════════════════════════════════════════════════════
fig3, ax3 = plt.subplots(figsize=(11, 5))
fig3.patch.set_facecolor('#0F172A')
ax3.set_facecolor('#1E293B')

ax3.bar(x - width/2, write_back['checkpoint_cycles'], width,
        label='Write-Back (NACHO baseline)', color=WB_COLOR, alpha=0.88)
ax3.bar(x + width/2, write_through_v2['checkpoint_cycles'], width,
        label='Write-Through (this work)', color=WT_COLOR, alpha=0.88)

for i, v in enumerate(write_back['checkpoint_cycles']):
    pct = v / write_back['cycles'][i] * 100
    ax3.text(i - width/2, v * 1.02, f'{pct:.0f}%',
             ha='center', va='bottom', fontsize=8, color='#93C5FD')

ax3.set_xticks(x)
ax3.set_xticklabels(bench_labels, color='#CBD5E1', fontsize=10)
ax3.set_ylabel('Checkpoint Overhead Cycles', color='#CBD5E1', fontsize=11)
ax3.set_title('Checkpoint Cycle Overhead\n'
              '(% labels show fraction of total cycles spent on checkpointing)',
              color='white', fontsize=13, fontweight='bold', pad=12)
ax3.tick_params(colors='#94A3B8')
ax3.spines['bottom'].set_color('#334155')
ax3.spines['left'].set_color('#334155')
ax3.spines['top'].set_visible(False)
ax3.spines['right'].set_visible(False)
ax3.legend(fontsize=10, facecolor='#1E293B', labelcolor='white',
           edgecolor='#334155')
ax3.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f'{int(v):,}'))
ax3.grid(axis='y', alpha=0.15, color='white')
ax3.yaxis.label.set_color('#94A3B8')

plt.tight_layout()
plt.savefig('results/wt_checkpoint_cycles.png', dpi=150, bbox_inches='tight',
            facecolor='#0F172A')
print("Saved: results/wt_checkpoint_cycles.png")

print("\n=== Summary Table ===")
print(f"{'Benchmark':<12} {'WB Cycles':>14} {'WT Cycles':>14} {'Ratio':>8} {'WB CKPs':>9} {'WT CKPs':>8}")
print("─"*70)
for i, b in enumerate(benchmarks):
    ratio = write_through_v2['cycles'][i] / write_back['cycles'][i]
    trend = "✓ faster" if ratio < 1.0 else ""
    print(f"{b:<12} {write_back['cycles'][i]:>14,} {write_through_v2['cycles'][i]:>14,} "
          f"{ratio:>7.2f}× {write_back['checkpoints'][i]:>9,} {write_through_v2['checkpoints'][i]:>8}  {trend}")
