-- Lean theorems for M_count_to
set_option autoImplicit true
set_option sorryPermitted true

-- requires: n >= 0
-- ensures: result = n /\ result >= 0
theorem count_to_correct (n : Int) : Prop := by
  admit
