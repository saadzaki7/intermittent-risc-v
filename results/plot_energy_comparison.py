#!/usr/bin/env python3
"""
Energy Comparison: Write-Back vs Write-Through
NACHO Framework — using Nigel's energy model constants + v3 accurate benchmark data

Phase 1 limitation: Nigel's plugin treats all memory as cache, so NVM energy is computed
offline here using the byte counts from our custom cache plugin stats.

Energy constants (from Nigel's EnergyTracking.cpp):
  CPU instruction: 0.5 pJ
  Cache read:      0.2 pJ/byte
  Cache write:     0.3 pJ/byte
  NVM read:        2.0 pJ/byte
  NVM write:       5.0 pJ/byte
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

benchmarks = ['adpcm', 'aes', 'coremark', 'crc', 'dijkstra', 'picojpeg', 'quicksort', 'sha', 'towers']

# ── Nigel's energy constants (pJ) ──
CPU_INSN_ENERGY    = 0.5      # per instruction
CACHE_READ_ENERGY  = 0.2      # per byte
CACHE_WRITE_ENERGY = 0.3      # per byte
NVM_READ_ENERGY    = 2.0      # per byte
NVM_WRITE_ENERGY   = 5.0      # per byte

# ── Write-Back (NACHO baseline) — live from energy_eval.log ──
# Cache plugin fields
wb_cycles        = [59880658, 15222556, 4068117, 44788, 130907217, 91571886, 1929982, 34142022, 7831281]
wb_checkpoints   = [2739,     751,      207,     4,     33946,     79559,    333,     2437,     3155]
wb_ckpt_cycles   = [3391926,  1024330,  267244,  5444,  24635228,  53789832, 396086,  4216712,  2967994]
wb_nvm_reads     = [2086424,  314712,   123592,  2092,  23278120,  14191380, 152640,  2071256,  745872]
wb_nvm_writes    = [1939064,  526988,   141660,  2832,  11505672,  24555564, 201096,  2300604,  1452000]
wb_cache_reads   = [1876666,  1342052,  984004,  2332,  24598721,  8535928,  1089196, 8228128,  2294148]
wb_cache_writes  = [1697402,  1079678,  520380,  3097,  24631520,  6965948,  281632,  3341865,  2380320]
# Nigel's plugin output (CPU + cache only, NVM=0 in Phase 1)
wb_plugin_total  = [24897463, 6136059,  1677093, 16777, 34066727,  15405330, 699959,  12638857, 2625514]
wb_instrs        = [46492044, 10973027, 2651356, 30742, 52903994,  24164348, 826708,  20464448, 2917459]

# ── Write-Through (Saad's implementation) — live from energy_eval.log ──
wt_cycles        = [266179414, 552240162, 39899831, 443768, 171501253, 812293980, 16558970, 413481244, 104715857]
wt_checkpoints   = [344357,    879549,    59096,    663,    109450,    1269117,   24687,    628831,    163887]
wt_ckpt_cycles   = [210746484, 538283988, 36166752, 405756, 66983400,  776699604, 15108444, 384844572, 100298844]
wt_nvm_reads     = [48056284,  119669892, 8092336,  90860,  32443728,  174514204, 3409844,  86482192,  22309100]
wt_nvm_writes    = [93665104,  239237328, 16074112, 180336, 29770400,  345199824, 6714864,  171042032, 44577264]
wt_cache_reads   = wb_cache_reads   # same binary
wt_cache_writes  = wb_cache_writes
wt_instrs        = wb_instrs        # same binary

def compute_energy(insns, cr, cw, nr, nw):
    cpu   = [i * CPU_INSN_ENERGY    for i in insns]
    cache_r = [b * CACHE_READ_ENERGY  for b in cr]
    cache_w = [b * CACHE_WRITE_ENERGY for b in cw]
    nvm_r = [b * NVM_READ_ENERGY    for b in nr]
    nvm_w = [b * NVM_WRITE_ENERGY   for b in nw]
    total = [cpu[i] + cache_r[i] + cache_w[i] + nvm_r[i] + nvm_w[i]
             for i in range(len(insns))]
    return total, cpu, cache_r, cache_w, nvm_r, nvm_w

wb_total, wb_cpu, wb_cr, wb_cw, wb_nr, wb_nw = compute_energy(
    wb_instrs, wb_cache_reads, wb_cache_writes, wb_nvm_reads, wb_nvm_writes)
wt_total, wt_cpu, wt_cr, wt_cw, wt_nr, wt_nw = compute_energy(
    wt_instrs, wt_cache_reads, wt_cache_writes, wt_nvm_reads, wt_nvm_writes)

# Convert to nanojoules for readability
def to_nj(lst): return [v/1000 for v in lst]
wb_total_nj = to_nj(wb_total)
wt_total_nj = to_nj(wt_total)
norm_energy = [wt/wb for wt, wb in zip(wt_total, wb_total)]

x = np.arange(len(benchmarks))
width = 0.38
WB_COLOR = '#3B82F6'
WT_COLOR = '#EF4444'

def style_ax(ax):
    ax.set_facecolor('#1E293B')
    ax.tick_params(colors='#94A3B8')
    ax.spines['bottom'].set_color('#334155')
    ax.spines['left'].set_color('#334155')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.label.set_color('#94A3B8')
    ax.grid(axis='y', alpha=0.15, color='white')
    ax.set_xticks(x)
    ax.set_xticklabels(benchmarks, color='#CBD5E1', fontsize=10)
    ax.legend(fontsize=10, facecolor='#1E293B', labelcolor='white', edgecolor='#334155')

# Fig 1: Total Energy (normalised)
fig1, ax1 = plt.subplots(figsize=(11, 5))
fig1.patch.set_facecolor('#0F172A')
ax1.bar(x - width/2, [1.0]*len(benchmarks), width, label='Write-Back (Baseline)', color=WB_COLOR)
ax1.bar(x + width/2, norm_energy, width, label='Write-Through (Accurate)', color=WT_COLOR)
for i, v in enumerate(norm_energy):
    ax1.text(i + width/2, max(v+0.02, 0.08), f'{v:.1f}X', ha='center', va='bottom',
             fontsize=8.5, fontweight='bold', color='#FCA5A5')
ax1.axhline(1.0, color='white', linewidth=0.8, linestyle='--')
ax1.set_ylabel('Normalised Total Energy (pJ)', color='#CBD5E1')
ax1.set_title('Total Energy Consumption: Write-Through vs Write-Back\n'
              '(Accounting for CPU, Cache SRAM, and NVM via Nigel\'s model)',
              color='white', fontweight='bold', pad=12)
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f'{v:.1f}X'))
ax1.set_ylim(0, max(norm_energy)*1.15)
style_ax(ax1)
fig1.tight_layout()
fig1.savefig('results/wt_v3_energy_comparison.png', dpi=150, bbox_inches='tight', facecolor='#0F172A')
print("Saved: results/wt_v3_energy_comparison.png")

# Fig 2: Energy component stacked bar (Write-Through)
fig2, (ax2a, ax2b) = plt.subplots(1, 2, figsize=(14, 5))
fig2.patch.set_facecolor('#0F172A')

def stacked(ax, cpu, cr, cw, nr, nw, title):
    cpu_nj = to_nj(cpu); cr_nj = to_nj(cr); cw_nj = to_nj(cw)
    nr_nj = to_nj(nr); nw_nj = to_nj(nw)
    ax.bar(x, cpu_nj, label='CPU', color='#818CF8')
    ax.bar(x, cr_nj,  bottom=cpu_nj, label='Cache Read', color='#34D399')
    ax.bar(x, cw_nj,  bottom=[cpu_nj[i]+cr_nj[i] for i in range(len(x))], label='Cache Write', color='#FBBF24')
    ax.bar(x, nr_nj,  bottom=[cpu_nj[i]+cr_nj[i]+cw_nj[i] for i in range(len(x))], label='NVM Read', color='#F87171')
    ax.bar(x, nw_nj,  bottom=[cpu_nj[i]+cr_nj[i]+cw_nj[i]+nr_nj[i] for i in range(len(x))], label='NVM Write', color='#EF4444')
    ax.set_title(title, color='white', fontweight='bold')
    ax.set_ylabel('Energy (nJ)', color='#CBD5E1')
    style_ax(ax)

stacked(ax2a, wb_cpu, wb_cr, wb_cw, wb_nr, wb_nw, 'Write-Back Energy Breakdown')
stacked(ax2b, wt_cpu, wt_cr, wt_cw, wt_nr, wt_nw, 'Write-Through Energy Breakdown')
fig2.tight_layout()
fig2.savefig('results/wt_v3_energy_breakdown.png', dpi=150, bbox_inches='tight', facecolor='#0F172A')
print("Saved: results/wt_v3_energy_breakdown.png")

print("\n=== Energy Summary (Nigel's model applied to v3 byte counts) ===")
print(f"{'Benchmark':<12} {'WB Energy (nJ)':>16} {'WT Energy (nJ)':>16} {'Ratio':>8}")
print("─"*60)
for i, b in enumerate(benchmarks):
    print(f"{b:<12} {wb_total_nj[i]:>16.1f} {wt_total_nj[i]:>16.1f} {norm_energy[i]:>7.2f}X")
