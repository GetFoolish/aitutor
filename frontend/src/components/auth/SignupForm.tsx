/**
 * Signup form for new users - Multi-step wizard
 */
import React, { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { authAPI } from "../../lib/auth-api";
import BackgroundShapes from "../background-shapes/BackgroundShapes";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";


// Zod Schema for Validation
const signupSchema = z.object({
  userType: z.enum(["student", "parent"]),
  age: z.coerce.number().min(5, "Age must be at least 5").max(18, "Age must be under 18"),
  // Step 2
  subjects: z.array(z.string()).min(1, "Select at least one subject"),
  learningGoals: z.array(z.string()).min(1, "Select at least one goal"),
  // Step 3
  interests: z.array(z.string()).min(1, "Select at least one interest"),
  learningStyle: z.string().min(1, "Please select a learning style"),
});

type SignupFormData = z.infer<typeof signupSchema>;

interface SignupFormProps {
  setupToken: string;
  googleUser: any;
  onComplete: (token: string, user: any) => void;
  onCancel: () => void;
}

const STEPS = [
  { id: 1, title: "Basic Info", description: "Let's get to know you" },
  { id: 2, title: "Academics", description: "What do you want to learn?" },
  { id: 3, title: "Personalization", description: "How do you learn best?" },
];

// Predefined Options
const SUBJECTS = ["Math", "Science", "English", "History", "Coding", "Arts"];
const GOALS = [
  "Improve Grades",
  "Prepare for Exams",
  "Learn New Skills",
  "Homework Help",
  "Just for Fun",
];
const INTERESTS = [
  "Space & Astronomy",
  "Robots & AI",
  "Nature & Animals",
  "Video Games",
  "Music & Dance",
  "Sports",
  "Reading & Writing",
];
const LEARNING_STYLES = [
  { value: "visual", label: "Visual (I learn by seeing)", icon: "visibility" },
  { value: "auditory", label: "Auditory (I learn by listening)", icon: "headphones" },
  { value: "kinesthetic", label: "Kinesthetic (I learn by doing)", icon: "sports_handball" },
  { value: "reading", label: "Reading/Writing (I learn by reading)", icon: "menu_book" },
];


const SignupForm: React.FC<SignupFormProps> = ({ setupToken, googleUser, onComplete, onCancel }) => {
  const [step, setStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const {
    control,
    handleSubmit,
    trigger,
    watch,
    formState: { errors, isValid },
  } = useForm<SignupFormData>({
    resolver: zodResolver(signupSchema) as any,
    defaultValues: {
      userType: "student",
      age: undefined,
      subjects: [],
      learningGoals: [],
      interests: [],
      learningStyle: "visual",
    },
    mode: "onChange",
  });

  const nextStep = async () => {
    let isValidStep = false;
    if (step === 1) {
      isValidStep = await trigger(["userType", "age"]);
    } else if (step === 2) {
      isValidStep = await trigger(["subjects", "learningGoals"]);
    }

    if (isValidStep) {
      setStep((prev) => prev + 1);
    }
  };

  const prevStep = () => {
    setStep((prev) => prev - 1);
  };

  const onSubmit = async (data: SignupFormData) => {
    setIsSubmitting(true);
    setSubmitError("");

    try {
      const response = await authAPI.completeSetup(setupToken, data.userType, data.age, {
        subjects: data.subjects,
        learningGoals: data.learningGoals,
        interests: data.interests,
        learningStyle: data.learningStyle,
      });
      onComplete(response.token, response.user);
    } catch (err: any) {
      setSubmitError(err.message || "Failed to complete setup.");
      setIsSubmitting(false);
    }
  };

  const currentProgress = (step / STEPS.length) * 100;

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4 font-sans">
      <BackgroundShapes />

      <div className="relative z-10 w-full max-w-lg overflow-hidden rounded-xl border border-border/50 bg-card/95 shadow-2xl backdrop-blur-xl">
        {/* Header */}
        <div className="bg-muted/30 p-6 text-center">
          {/* Logo Badge */}
          <div className="mx-auto mb-4 flex h-14 w-14 rotate-3 items-center justify-center rounded-lg border-2 border-primary bg-primary/20 shadow-lg">
            <span className="material-symbols-outlined text-3xl text-primary font-bold">
              school
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            {STEPS[step - 1].title}
          </h1>
          <p className="text-sm text-muted-foreground">{STEPS[step - 1].description}</p>

          <div className="mt-6">
            <Progress value={currentProgress} className="h-2" />
            <div className="mt-2 flex justify-between text-[10px] uppercase tracking-wider text-muted-foreground">
              <span>Step {step} of 3</span>
              <span>{Math.round(currentProgress)}% Completed</span>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="p-6">
          <div className="min-h-[300px]">
            {step === 1 && (
              <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                <div className="space-y-3">
                  <Label className="text-base font-semibold">I am a...</Label>
                  <Controller
                    name="userType"
                    control={control}
                    render={({ field }) => (
                      <RadioGroup
                        onValueChange={field.onChange}
                        defaultValue={field.value}
                        className="grid grid-cols-2 gap-4"
                      >
                        <div>
                          <RadioGroupItem value="student" id="student" className="peer sr-only" />
                          <Label
                            htmlFor="student"
                            className="flex flex-col items-center justify-between rounded-md border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary peer-data-[state=checked]:text-primary cursor-pointer transition-all"
                          >
                            <span className="material-symbols-outlined mb-2 text-2xl">person</span>
                            Student
                          </Label>
                        </div>
                        <div>
                          <RadioGroupItem value="parent" id="parent" className="peer sr-only" />
                          <Label
                            htmlFor="parent"
                            className="flex flex-col items-center justify-between rounded-md border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary peer-data-[state=checked]:text-primary cursor-pointer transition-all"
                          >
                            <span className="material-symbols-outlined mb-2 text-2xl">supervisor_account</span>
                            Parent
                          </Label>
                        </div>
                      </RadioGroup>
                    )}
                  />
                </div>

                <div className="space-y-3">
                  <Label htmlFor="age" className="text-base font-semibold">
                    How old are you?
                  </Label>
                  <Controller
                    name="age"
                    control={control}
                    render={({ field }) => (
                      <div className="relative">
                        <Input
                          {...field}
                          value={field.value ?? ''}
                          id="age"
                          type="number"
                          placeholder="Enter age (5-18)"
                          className="h-12 text-lg"
                          onChange={(e) => field.onChange(e.target.valueAsNumber)}
                          min={5}
                          max={18}
                        />
                        <div className="absolute right-3 top-3 text-muted-foreground">
                          <span className="material-symbols-outlined">cake</span>
                        </div>
                      </div>
                    )}
                  />
                  {errors.age && <p className="text-sm font-medium text-destructive">{errors.age.message}</p>}
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                <div className="space-y-3">
                  <Label className="text-base font-semibold">Which subjects do you need help with?</Label>
                  <Controller
                    name="subjects"
                    control={control}
                    render={({ field }) => (
                      <div className="grid grid-cols-2 gap-3">
                        {SUBJECTS.map((subject) => (
                          <div key={subject} className="flex items-center space-x-2 rounded-md border p-3 hover:bg-accent">
                            <Checkbox
                              id={`subject-${subject}`}
                              checked={field.value.includes(subject)}
                              onCheckedChange={(checked) => {
                                if (checked) {
                                  field.onChange([...field.value, subject]);
                                } else {
                                  field.onChange(field.value.filter((val) => val !== subject));
                                }
                              }}
                            />
                            <label htmlFor={`subject-${subject}`} className="cursor-pointer text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                              {subject}
                            </label>
                          </div>
                        ))}
                      </div>
                    )}
                  />
                  {errors.subjects && <p className="text-sm font-medium text-destructive">{errors.subjects.message}</p>}
                </div>

                <div className="space-y-3">
                  <Label className="text-base font-semibold">What are your learning goals?</Label>
                  <Controller
                    name="learningGoals"
                    control={control}
                    render={({ field }) => (
                      <div className="space-y-2">
                        {GOALS.map((goal) => (
                          <div key={goal} className="flex items-center space-x-2">
                            <Checkbox
                              id={`goal-${goal}`}
                              checked={field.value.includes(goal)}
                              onCheckedChange={(checked) => {
                                if (checked) {
                                  field.onChange([...field.value, goal]);
                                } else {
                                  field.onChange(field.value.filter((val) => val !== goal));
                                }
                              }}
                            />
                            <label htmlFor={`goal-${goal}`} className="text-sm font-medium leading-none">
                              {goal}
                            </label>
                          </div>
                        ))}
                      </div>
                    )}
                  />
                  {errors.learningGoals && <p className="text-sm font-medium text-destructive">{errors.learningGoals.message}</p>}
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                <div className="space-y-3">
                  <Label className="text-base font-semibold">What are your interests?</Label>
                  <p className="text-xs text-muted-foreground">We'll use these to make problems more fun!</p>
                  <Controller
                    name="interests"
                    control={control}
                    render={({ field }) => (
                      <div className="flex flex-wrap gap-2">
                        {INTERESTS.map((interest) => {
                          const isSelected = field.value.includes(interest);
                          return (
                            <div
                              key={interest}
                              onClick={() => {
                                if (isSelected) {
                                  field.onChange(field.value.filter((i) => i !== interest));
                                } else {
                                  field.onChange([...field.value, interest]);
                                }
                              }}
                              className={`cursor-pointer rounded-full border px-3 py-1.5 text-sm transition-colors ${isSelected
                                ? "bg-primary text-primary-foreground border-primary hover:bg-primary/90"
                                : "bg-background hover:bg-accent hover:text-accent-foreground"
                                }`}
                            >
                              {isSelected && <span className="mr-1">✓</span>}
                              {interest}
                            </div>
                          )
                        })}
                      </div>
                    )}
                  />
                  {errors.interests && <p className="text-sm font-medium text-destructive">{errors.interests.message}</p>}
                </div>

                <div className="space-y-3">
                  <Label className="text-base font-semibold">How do you prefer to learn?</Label>
                  <Controller
                    name="learningStyle"
                    control={control}
                    render={({ field }) => (
                      <RadioGroup
                        onValueChange={field.onChange}
                        defaultValue={field.value}
                        className="grid grid-cols-1 gap-2"
                      >
                        {LEARNING_STYLES.map((style) => (
                          <div key={style.value} className="flex items-center space-x-2 rounded-lg border p-3 hover:bg-accent/50 has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-accent">
                            <RadioGroupItem value={style.value} id={`style-${style.value}`} />
                            <Label htmlFor={`style-${style.value}`} className="flex flex-1 cursor-pointer items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="material-symbols-outlined text-muted-foreground">{style.icon}</span>
                                <span className="font-medium">{style.label.split("(")[0]}</span>
                              </div>
                            </Label>
                          </div>
                        ))}
                      </RadioGroup>
                    )}
                  />
                </div>
              </div>
            )}
          </div>

          {submitError && (
            <div className="mb-4 rounded-md bg-destructive/15 p-3 text-sm text-destructive">
              {submitError}
            </div>
          )}

          <div className="mt-6 flex justify-between gap-4 border-t pt-6">
            <Button
              type="button"
              variant="outline"
              onClick={step === 1 ? onCancel : prevStep}
              disabled={isSubmitting}
            >
              {step === 1 ? "Cancel" : "Back"}
            </Button>

            {step < 3 ? (
              <Button type="button" onClick={nextStep}>
                Next Step
                <span className="material-symbols-outlined ml-2 text-base">arrow_forward</span>
              </Button>
            ) : (
              <Button type="submit" disabled={isSubmitting} className="min-w-[120px]">
                {isSubmitting ? "Finishing..." : "Start Learning!"}
              </Button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
};

export default SignupForm;
