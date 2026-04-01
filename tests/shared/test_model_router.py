from shared import model_router


def test_classify_task_complexity_chooses_expected_tiers():
    router = model_router.ModelRouter()

    assert router.classify_task_complexity("greeting", context_length=10) is model_router.ComplexityTier.SIMPLE
    assert router.classify_task_complexity("grading", requires_reasoning=True) is model_router.ComplexityTier.COMPLEX
    assert router.classify_task_complexity("grading", is_final_assessment=True) is model_router.ComplexityTier.CRITICAL
    assert router.classify_task_complexity("explanation", context_length=500) is model_router.ComplexityTier.MODERATE


def test_route_request_updates_usage_stats():
    router = model_router.ModelRouter()

    config, complexity = router.route_request("greeting", prompt="hello")

    assert complexity is model_router.ComplexityTier.SIMPLE
    assert config.provider == "google"
    assert router.usage_stats[model_router.ModelTier.FAST]["calls"] == 1


def test_select_model_estimate_cost_and_stats():
    router = model_router.ModelRouter()
    premium = router.select_model(model_router.ComplexityTier.CRITICAL)
    cost = router.estimate_cost(model_router.ModelTier.PREMIUM, input_tokens=500, output_tokens=500)
    stats = router.get_stats()

    assert premium.name == "gpt-4-turbo"
    assert cost == 0.01
    assert stats["total_calls"] == 0
    assert set(stats["tier_distribution"]) == {"fast", "standard", "advanced", "premium"}


def test_global_router_helpers():
    model, complexity = model_router.route_llm_request("grading", prompt="Explain fractions", requires_reasoning=True)
    stats = model_router.get_routing_stats()

    assert complexity is model_router.ComplexityTier.COMPLEX
    assert model.name == "gemini-1.5-pro"
    assert stats["total_calls"] >= 1
