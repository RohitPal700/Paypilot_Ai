"""
Business-policy layer that converts a raw failure probability into a
coarse risk tier (low / medium / high).

IMPORTANT: the thresholds below are an INITIAL MVP POLICY, not a
mathematically derived optimum. They were chosen as a reasonable starting
point for a "flag for review" workflow, informed by (but not equal to) the
decision-threshold analysis done separately for the model's own 0.5 default
classification cutoff (see app/ml/threshold_analysis.py). That analysis
showed no single threshold is clearly "best" for this model without knowing
the actual business cost of a false alarm vs. a missed failure -- so these
tier boundaries should be revisited once real usage data or an explicit
cost model is available, not treated as fixed.

Keeping this as a standalone module (rather than inlining if/else logic in
the API endpoint) means the thresholds can be changed, tuned, or made
configurable (e.g. via environment variables or a config file) later
without touching request handling, validation, or model-loading code.
"""

from app.schemas.ml import RiskTier

# Initial MVP policy thresholds -- see module docstring.
LOW_THRESHOLD = 0.20   # probability < LOW_THRESHOLD          -> low
HIGH_THRESHOLD = 0.40  # probability >= HIGH_THRESHOLD         -> high
# LOW_THRESHOLD <= probability < HIGH_THRESHOLD                -> medium


def probability_to_risk_tier(probability: float) -> RiskTier:
    """
    Map a failure probability in [0, 1] to a RiskTier using the policy
    thresholds above. Boundaries are inclusive on the lower/upper ends as
    documented (< LOW_THRESHOLD is low, >= HIGH_THRESHOLD is high).
    """
    if probability < LOW_THRESHOLD:
        return RiskTier.LOW
    if probability < HIGH_THRESHOLD:
        return RiskTier.MEDIUM
    return RiskTier.HIGH