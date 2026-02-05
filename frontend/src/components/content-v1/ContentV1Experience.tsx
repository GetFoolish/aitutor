import React, { useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { apiUtils } from "../../lib/api-utils";
import { ServerItemRenderer } from "../../package/perseus/src/server-item-renderer";
import { storybookDependenciesV2 } from "../../package/perseus/testing/test-dependencies";
import { RenderStateRoot } from "@khanacademy/wonder-blocks-core";
import { PerseusI18nContextProvider } from "../../package/perseus/src/components/i18n-context";
import { mockStrings } from "../../package/perseus/src/strings";
import { scorePerseusItem } from "@khanacademy/perseus-score";

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || "http://localhost:8000";
const PROFILE_KEY = "content_v1_profile_id";
const CONTENT_V1_STARTED_KEY = "content_v1_started";
const CONTENT_V1_MODE_KEY = "content_v1_mode";

type Step = { id?: string; topic?: string; title?: string; description?: string };
type Plan = { title?: string; steps?: Step[] };

const ContentV1Experience: React.FC = () => {
  const rendererRef = useRef<ServerItemRenderer>(null);
  const [age, setAge] = useState("10");
  const [goal, setGoal] = useState("");
  const [loading, setLoading] = useState(false);
  const [profileId, setProfileId] = useState<string>(() => localStorage.getItem(PROFILE_KEY) || "");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [question, setQuestion] = useState<any | null>(null);
  const [resultText, setResultText] = useState<string>("");
  const [submitted, setSubmitted] = useState(false);
  const [questionStartMs, setQuestionStartMs] = useState<number>(Date.now());

  React.useEffect(() => {
    sessionStorage.setItem(CONTENT_V1_MODE_KEY, "true");
    return () => {
      sessionStorage.removeItem(CONTENT_V1_MODE_KEY);
    };
  }, []);

  const currentStep = useMemo(() => {
    const steps = plan?.steps || [];
    if (!steps.length) return null;
    return steps[Math.min(currentStepIndex, steps.length - 1)];
  }, [plan, currentStepIndex]);

  const scoreCurrentQuestion = () => {
    if (!rendererRef.current || !question) return false;
    const userInput = rendererRef.current.getUserInput();
    try {
      const questionData = question.question;
      const scoreResult = scorePerseusItem(questionData, userInput, "en");
      return !!scoreResult?.correct;
    } catch (err) {
      console.warn("[ContentV1] Scoring failed, falling back to incorrect.", err);
      return false;
    }
  };

  const handleOnboarding = async () => {
    if (!goal.trim()) return;
    setLoading(true);
    setResultText("");
    try {
      const response = await apiUtils.post(`${DASH_API_URL}/api/content-v1/onboarding`, {
        age: Number(age),
        learning_goal: goal.trim(),
      });
      if (!response.ok) throw new Error(`Onboarding failed: ${response.status}`);
      const data = await response.json();
      setProfileId(data.learner_profile_id);
      setPlan(data.learning_plan || null);
      setQuestion(data.first_question || null);
      setCurrentStepIndex(0);
      setSubmitted(false);
      setQuestionStartMs(Date.now());
      localStorage.setItem(PROFILE_KEY, data.learner_profile_id);
      sessionStorage.setItem(CONTENT_V1_STARTED_KEY, "true");
    } catch (e: any) {
      setResultText(e?.message || "Failed to create plan");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!profileId || !question || submitted) return;
    const isCorrect = scoreCurrentQuestion();
    const responseTimeMs = Date.now() - questionStartMs;
    setLoading(true);
    try {
      const response = await apiUtils.post(`${DASH_API_URL}/api/content-v1/questions/submit`, {
        learner_profile_id: profileId,
        question_id: question?.dash_metadata?.dash_question_id,
        is_correct: isCorrect,
        response_time_ms: responseTimeMs,
        signals: {},
      });
      if (!response.ok) throw new Error(`Submit failed: ${response.status}`);
      const data = await response.json();
      setSubmitted(true);
      setResultText(isCorrect ? "Nice work. Correct." : "Not quite yet. Let's keep going.");
      setCurrentStepIndex(data?.updated_progress?.current_step_index ?? 0);
    } catch (e: any) {
      setResultText(e?.message || "Failed to submit answer");
    } finally {
      setLoading(false);
    }
  };

  const handleNext = async () => {
    if (!profileId) return;
    setLoading(true);
    setResultText("");
    try {
      const response = await apiUtils.get(
        `${DASH_API_URL}/api/content-v1/questions/next?learner_profile_id=${encodeURIComponent(profileId)}`,
      );
      if (!response.ok) throw new Error(`Next question failed: ${response.status}`);
      const data = await response.json();
      setQuestion(data.question || null);
      setSubmitted(false);
      setQuestionStartMs(Date.now());
    } catch (e: any) {
      setResultText(e?.message || "Failed to load next question");
    } finally {
      setLoading(false);
    }
  };

  if (!profileId || !plan || !question) {
    return (
      <div className="w-full flex justify-center py-8">
        <Card className="w-full max-w-3xl border-[4px] border-black bg-[#FFFDF5]">
          <CardHeader className="font-black text-3xl uppercase">Build Your Learning Journey</CardHeader>
          <CardContent className="space-y-3">
            <label className="block text-sm font-bold uppercase">Age</label>
            <input
              className="w-full border-[3px] border-black p-2 font-mono"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              type="number"
              min={5}
              max={18}
            />
            <label className="block text-sm font-bold uppercase">What do you want to learn?</label>
            <input
              className="w-full border-[3px] border-black p-2 font-mono"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="e.g. World history, coding in Python, guitar basics"
            />
            {resultText ? <p className="text-sm font-bold text-red-600">{resultText}</p> : null}
          </CardContent>
          <CardFooter>
            <Button className="border-[3px] border-black bg-[#C4B5FD] text-black font-black" disabled={loading} onClick={handleOnboarding}>
              {loading ? "Creating Plan..." : "Create Plan"}
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  return (
    <div className="w-full space-y-4">
      <Card className="border-[4px] border-black bg-[#FFFDF5]">
        <CardHeader className="font-black uppercase">
          {plan.title || "Your Learning Journey"}
        </CardHeader>
        <CardContent className="space-y-2">
          {(plan.steps || []).map((step, idx) => (
            <div
              key={`${step.id || step.title || idx}`}
              className={`border-[3px] p-2 font-bold ${idx === currentStepIndex ? "bg-[#C9F18D]" : "bg-white"}`}
            >
              {idx + 1}. {step.title || step.topic || "Step"} - {step.description || ""}
            </div>
          ))}
          {currentStep ? (
            <div className="text-sm font-bold uppercase">Current: {currentStep.title || currentStep.topic}</div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border-[4px] border-black bg-white">
        <CardContent className="p-4">
          <PerseusI18nContextProvider locale="en" strings={mockStrings}>
            <RenderStateRoot>
              <ServerItemRenderer
                ref={rendererRef}
                problemNum={0}
                item={question}
                dependencies={storybookDependenciesV2}
                apiOptions={{}}
                linterContext={{ contentType: "", highlightLint: true, paths: [], stack: [] }}
                showSolutions="none"
                hintsVisible={0}
                reviewMode={false}
              />
            </RenderStateRoot>
          </PerseusI18nContextProvider>
        </CardContent>
        <CardFooter className="flex gap-2">
          <Button className="border-[3px] border-black bg-[#C4B5FD] text-black font-black" onClick={handleSubmit} disabled={loading || submitted}>
            Submit
          </Button>
          <Button className="border-[3px] border-black bg-[#FFD93D] text-black font-black" onClick={handleNext} disabled={loading}>
            Next
          </Button>
          <Button
            className="border-[3px] border-black bg-white text-black font-black"
            onClick={() => {
              localStorage.removeItem(PROFILE_KEY);
              sessionStorage.removeItem(CONTENT_V1_STARTED_KEY);
              setProfileId("");
              setPlan(null);
              setQuestion(null);
              setSubmitted(false);
              setResultText("");
            }}
          >
            Reset
          </Button>
        </CardFooter>
      </Card>

      {resultText ? <div className="font-black">{resultText}</div> : null}
    </div>
  );
};

export default ContentV1Experience;
