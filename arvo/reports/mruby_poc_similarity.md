# mruby PoC Knowledge Transfer Analysis

## Overview

- **in_cybergym=true**: 39 entries
- **in_cybergym=false**: 59 entries (KB pool)

---

## 1. Crash function mapping (28 non-cyb → 21 cyb, covering 21/39 cyb entries)

| Crash function (#0) | non-cyb | → cyb | Module | Transfer |
|---|---|---|---|---|
| `mrb_vm_exec` | 6 | 3 | VM | **one→many** — 6 entries teach patterns for 3 targets |
| `udiv` | 6 | 2 | BigInt | **one→many** — bigint division |
| `mrb_gc_mark` | 4 | 1 | GC | **many→one** — 4 teaching examples for 1 target |
| `ucmp` | 3 | 1 | BigInt | bigint comparison |
| `mrb_memsearch_ss` | 3 | 1 | String | string search overflow |
| `mark_context_stack` | 2 | 2 | GC | **1:1** — identical dedup |
| `mrb_byte_hash_step` | 2 | 1 | VM | bytecode hash collision |
| `str_init_embed` | 1 | 2 | String | **one→two** — string init |
| `obj_free` | 1 | 1 | GC | GC free path |
| `mrb_vm_exec` | *already counted* | | | |
| **Subtotal** | **28** | **13** | | |

## 2. Crash functions with NO non-cyb match (18 cyb entries uncovered by exact func)

These 18 cyb entries have NO exact crash function match in the KB. However, they still benefit from **module-level** transfer:

| Crash function | # cyb | Module | Module KB coverage |
|---|---|---|---|
| `__asan_memcpy` | 4 | String/heredoc | ✓ 32 non-cyb frames in String |
| `mrb_check_frozen` | 2 | VM | ✓ 100 non-cyb frames in VM |
| `mrb_format_float` | 3 | sprintf | ✓ 2 non-cyb frames |
| `digits` | 2 | BigInt | ✓ 47 non-cyb frames |
| `mrb_ary_shift_m` | 1 | Array | ✗ 0 (only gap) |
| `mrb_decode_insn` | 1 | VM | ✓ |
| `mrb_str_len_to_dbl` | 1 | String | ✓ |
| `presym_sym2name` | 1 | Symbol | ✓ |
| `read_tmpl` | 1 | Pack | ✓ |
| `unpack_bstr` | 1 | Pack | ✓ |
| `value_move` | 1 | Array | ✗ |
| `fmt_setup`, `lzb`, `dispatch`, `urshift`, `mpz_cmp`, `mpz_get_str`, `str_decref` | 1 each | various | ✓ |

**18/39 cyb entries have no exact func match but 16/18 still have module-level KB coverage.** Only 2 Array-related entries lack KB support.

## 3. Module-level coverage

Every major code module has non-cyb entries:

| Module | non-cyb frames | cyb frames | Gap |
|---|---|---|---|
| VM (vm.c) | 100 | 60 | ✓ covered |
| GC (gc.c) | 49 | 25 | ✓ covered |
| BigInt (bint.c) | 47 | 26 | ✓ covered |
| Compiler/Parser | 33 | 40 | ✓ covered |
| String (string.c) | 32 | 28 | ✓ covered |
| Class/Object | 13 | 1 | ✓ covered |
| Pack (pack.c) | 6 | 11 | ✓ covered |
| Symbol | 4 | 3 | ✓ covered |
| Error | 3 | 1 | ✓ covered |
| Array | 0 | 4 | **gap** |

## 4. One-to-many transfer patterns

### Pattern A: Same bug site, different crash type
```
non-cyb mrb_vm_exec (6 entries, various crash types)
  → cyb 42499386  Heap-buffer-overflow READ
  → cyb 42501369  UNKNOWN WRITE
  → cyb 42513594  Heap-buffer-overflow WRITE
```
One code location (`vm.c` around line 1140) produces multiple crash type variants. Learning the vulnerable VM opcodes from any entry applies to all.

### Pattern B: Same function, different callers
```
non-cyb mrb_memsearch_ss (via str_split_m) 
  → cyb mrb_memsearch_ss (via str_index)
```
The vulnerable function is identical (`string.c:619`, same line). Only the API entry differs.

### Pattern C: Same module, related functions
```
non-cyb udiv (BigInt division) → cyb udiv (same)
non-cyb ucmp (BigInt comparison) → cyb ucmp (same)
```
BigInt operations share a common pattern: malformed large integers cause uninitialized reads across all operations.

## 5. What the KB teaches for each cyb entry

For **every** cyb entry, the KB provides at least one of:

| Level | Covers | What agent learns |
|---|---|---|
| Exact func match | 21/39 (54%) | Exact crash site, stack trace, PoC input structure |
| Module-level | 16/39 (41%) | Adjacent functions in same source file, coding patterns |
| No coverage | 2/39 (5%) | Array operations only |

## Conclusion

**The KB is viable.** 54% of cyb entries have exact crash function matches in the non-cyb pool. 95% have at least module-level coverage. The one-to-many transfer is particularly strong: 6 `mrb_vm_exec` KB entries inform 3 cyb targets across 3 different crash types. The only weak spot is Array module (0 non-cyb entries), affecting 2 cyb targets.
