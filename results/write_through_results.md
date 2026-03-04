# Write-Through Results: nacho-write-through
# Config: 512B cache, 2 lines, Os, enable-pw-bit=1, enable-stack-tracking=2, enable-write-through=1
# Log dir: /tmp/benchmark-logs/
# Captured: 2026-03-04

## adpcm

```
cache_miss:394278
cache_hit:727909
cache_read:1876666
cache_write:1697402
cache_cuckoo:0
cache_checkpoint:0
nvm_reads_no_cache:1385314
nvm_writes_no_cache:700962
nvm_reads:48056284
nvm_writes:93665104
checkpoint:344357
checkpoint_war:344357
checkpoint_dirty:0
checkpoint_period:0
checkpoint_max_cycles: 0
restore:0
checkpoint_cycles:210746484
restore_cycles:0
hints_given:0
max_dirty_ratio:0
cuckoo_iter:0
cycles:266179414
```

## aes

```
cache_miss:17316
cache_hit:2093031
cache_read:1342052
cache_write:1079678
cache_cuckoo:0
cache_checkpoint:0
nvm_reads_no_cache:1337552
nvm_writes_no_cache:1068886
nvm_reads:119669892
nvm_writes:239237328
checkpoint:879549
checkpoint_war:879549
checkpoint_dirty:0
checkpoint_period:0
checkpoint_max_cycles: 0
restore:0
checkpoint_cycles:538283988
restore_cycles:0
hints_given:0
max_dirty_ratio:0
cuckoo_iter:0
cycles:552240162
```

## coremark

```
cache_miss:17057
cache_hit:423716
cache_read:984004
cache_write:520380
cache_cuckoo:0
cache_checkpoint:0
nvm_reads_no_cache:957449
nvm_writes_no_cache:466476
nvm_reads:8092336
nvm_writes:16074112
checkpoint:59096
checkpoint_war:59096
checkpoint_dirty:0
checkpoint_period:0
checkpoint_max_cycles: 0
restore:0
checkpoint_cycles:36166752
restore_cycles:0
hints_given:0
max_dirty_ratio:0
cuckoo_iter:0
cycles:39899831
```

## crc

```
cache_miss:289
cache_hit:1328
cache_read:2332
cache_write:3097
cache_cuckoo:0
cache_checkpoint:0
nvm_reads_no_cache:2312
nvm_writes_no_cache:3045
nvm_reads:90860
nvm_writes:180336
checkpoint:663
checkpoint_war:663
checkpoint_dirty:0
checkpoint_period:0
checkpoint_max_cycles: 0
restore:0
checkpoint_cycles:405756
restore_cycles:0
hints_given:0
max_dirty_ratio:0
cuckoo_iter:0
cycles:443768
```

## dijkstra

```
cache_miss:4470031
cache_hit:3563222
cache_read:24598721
cache_write:24631520
cache_cuckoo:0
cache_checkpoint:0
nvm_reads_no_cache:21387458
nvm_writes_no_cache:7129132
nvm_reads:32443728
nvm_writes:29770400
checkpoint:109450
checkpoint_war:109450
checkpoint_dirty:0
checkpoint_period:0
checkpoint_max_cycles: 0
restore:0
checkpoint_cycles:66983400
restore_cycles:0
hints_given:0
max_dirty_ratio:0
cuckoo_iter:0
cycles:171501253
```

## picojpeg

```
cache_miss:494211
cache_hit:4665838
cache_read:8535928
cache_write:6965948
cache_cuckoo:0
cache_checkpoint:0
nvm_reads_no_cache:7773978
nvm_writes_no_cache:5653044
nvm_reads:174514204
nvm_writes:345199824
checkpoint:1269117
checkpoint_war:1269117
checkpoint_dirty:0
checkpoint_period:0
checkpoint_max_cycles: 0
restore:0
checkpoint_cycles:776699604
restore_cycles:0
hints_given:0
max_dirty_ratio:0
cuckoo_iter:0
cycles:812293980
```

## quicksort

```
cache_miss:18658
cache_hit:310946
cache_read:1089196
cache_write:281632
cache_cuckoo:0
cache_checkpoint:0
nvm_reads_no_cache:1089196
nvm_writes_no_cache:229220
nvm_reads:3409844
nvm_writes:6714864
checkpoint:24687
checkpoint_war:24687
checkpoint_dirty:0
checkpoint_period:0
checkpoint_max_cycles: 0
restore:0
checkpoint_cycles:15108444
restore_cycles:0
hints_given:0
max_dirty_ratio:0
cuckoo_iter:0
cycles:16558970
```

## sha

```
cache_miss:329471
cache_hit:3277903
cache_read:8228128
cache_write:3341865
cache_cuckoo:0
cache_checkpoint:0
nvm_reads_no_cache:7994254
nvm_writes_no_cache:2692565
nvm_reads:86482192
nvm_writes:171042032
checkpoint:628831
checkpoint_war:628831
checkpoint_dirty:0
checkpoint_period:0
checkpoint_max_cycles: 0
restore:0
checkpoint_cycles:384844572
restore_cycles:0
hints_given:0
max_dirty_ratio:0
cuckoo_iter:0
cycles:413481244
```

## towers

```
cache_miss:7325
cache_hit:1156175
cache_read:2294148
cache_write:2380320
cache_cuckoo:0
cache_checkpoint:0
nvm_reads_no_cache:2294148
nvm_writes_no_cache:2359852
nvm_reads:22309100
nvm_writes:44577264
checkpoint:163887
checkpoint_war:163887
checkpoint_dirty:0
checkpoint_period:0
checkpoint_max_cycles: 0
restore:0
checkpoint_cycles:100298844
restore_cycles:0
hints_given:0
max_dirty_ratio:0
cuckoo_iter:0
cycles:104715857
```
