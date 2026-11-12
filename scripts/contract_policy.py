"""Decisiones de sensibilidad que deben permanecer protegidas en los contratos."""

FCSE_ONLY_PATHS = frozenset(
    {
        "atalaya.v1.RemoteIdObservation.operator_id",
        "atalaya.v1.RemoteIdObservation.operator_location",
        "atalaya.v1.RemoteIdObservation.uas_id",
        "atalaya.v1.RemoteIdObservation.self_id_description",
        "atalaya.v1.Prediction.origin_heatmap",
        "atalaya.sim.v1.GroundTruth.true_position",
        "atalaya.sim.v1.GroundTruth.is_forged",
        "atalaya.sim.v1.GroundTruth.launch_point",
    }
)
