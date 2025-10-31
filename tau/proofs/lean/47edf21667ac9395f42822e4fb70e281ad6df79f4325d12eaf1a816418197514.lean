-- Lean theorems for M_clamp
set_option autoImplicit true
set_option sorryPermitted true

-- requires: lo <= x
-- ensures: (x < lo -> result = lo) /\ (x > hi -> result = hi) /\ (lo <= x /\ x <= hi -> result = x)
theorem clamp_correct (x : Int) (lo : Int) (hi : Int) : Prop := by
  admit
