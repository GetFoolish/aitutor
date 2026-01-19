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
import "./auth.scss";

// Zod Schema for Validation (only require basic info for simplified onboarding)
const signupSchema = z.object({
  userType: z.enum(["student", "parent"]),
  dateOfBirth: z.string().min(1, "Date of birth is required"),
  gender: z.string().min(1, "Please select your gender"),
  preferredLanguage: z.string().min(1, "Please select your preferred language"),
  // Optional fields kept for compatibility with API
  subjects: z.array(z.string()).optional(),
  learningGoals: z.array(z.string()).optional(),
  interests: z.array(z.string()).optional(),
  learningStyle: z.string().optional(),
});

type SignupFormData = z.infer<typeof signupSchema>;

interface SignupFormProps {
  setupToken: string;
  googleUser: any;
  onComplete: (token: string, user: any) => void;
  onCancel: () => void;
}

// Only keep the Basic Info step for streamlined onboarding
const STEPS = [{ id: 1, title: "Basic Info", description: "Let's get to know you" }];

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
const LANGUAGES = ["English", "Hindi", "Spanish", "French"];
const GENDERS = ["Male", "Female", "Other", "Prefer not to say"];


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
      dateOfBirth: "",
      gender: "",
      preferredLanguage: "",
      subjects: [],
      learningGoals: [],
      interests: [],
      learningStyle: "visual",
    },
    mode: "onChange",
  });

  const nextStep = async () => {
    // With single-step onboarding we don't need to advance
    const ok = await trigger(["userType", "dateOfBirth", "gender", "preferredLanguage"]);
    if (ok) setStep(1);
  };

  const prevStep = () => {
    setStep((prev) => prev - 1);
  };

  const onSubmit = async (data: SignupFormData) => {
    setIsSubmitting(true);
    setSubmitError("");

    try {
      // Provide safe defaults for optional profile data
      const profileData = {
        subjects: data.subjects || [],
        learningGoals: data.learningGoals || [],
        interests: data.interests || [],
        learningStyle: data.learningStyle || 'visual',
      };

      const response = await authAPI.completeSetup(
        setupToken,
        data.userType,
        data.dateOfBirth,
        data.gender,
        data.preferredLanguage,
        profileData
      );
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
                  <Label htmlFor="dateOfBirth" className="text-base font-semibold">
                    What's your date of birth?
                  </Label>
                  <Controller
                    name="dateOfBirth"
                    control={control}
                    render={({ field }) => (
                      <div className="relative">
                        <Input
                          {...field}
                          id="dateOfBirth"
                          type="date"
                          className="h-12 text-lg"
                        />
                        <div className="absolute right-3 top-3 text-muted-foreground">
                          <span className="material-symbols-outlined">cake</span>
                        </div>
                      </div>
                    )}
                  />
                  {errors.dateOfBirth && <p className="text-sm font-medium text-destructive">{errors.dateOfBirth.message}</p>}
                </div>

                <div className="space-y-3">
                  <Label htmlFor="gender" className="text-base font-semibold">
                    What's your gender?
                  </Label>
                  <Controller
                    name="gender"
                    control={control}
                    render={({ field }) => (
                      <Select onValueChange={field.onChange} value={field.value}>
                        <SelectTrigger className="h-12 text-lg">
                          <SelectValue placeholder="Select gender" />
                        </SelectTrigger>
                        <SelectContent>
                          {GENDERS.map((gender) => (
                            <SelectItem key={gender} value={gender}>
                              {gender}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  />
                  {errors.gender && <p className="text-sm font-medium text-destructive">{errors.gender.message}</p>}
                </div>

                <div className="space-y-3">
                  <Label htmlFor="preferredLanguage" className="text-base font-semibold">
                    What language are you most comfortable in?
                  </Label>
                  <Controller
                    name="preferredLanguage"
                    control={control}
                    render={({ field }) => (
                      <Select onValueChange={field.onChange} value={field.value}>
                        <SelectTrigger className="h-12 text-lg">
                          <SelectValue placeholder="Select language" />
                        </SelectTrigger>
                        <SelectContent>
                          {LANGUAGES.map((language) => (
                            <SelectItem key={language} value={language}>
                              {language}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  />
                  {errors.preferredLanguage && <p className="text-sm font-medium text-destructive">{errors.preferredLanguage.message}</p>}
                </div>
              </div>
            )}

            {/* Steps 2 and 3 removed for streamlined onboarding. Optional fields remain supported. */}
          </div>

          {submitError && (
            <div className="mb-4 rounded-md bg-destructive/15 p-3 text-sm text-destructive">
              {submitError}
            </div>
          )}

          <div className="mt-6 flex justify-end gap-4 border-t pt-6">
            <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>
              Cancel
            </Button>

            <Button type="submit" disabled={isSubmitting} className="min-w-[120px]">
              {isSubmitting ? "Finishing..." : "Start Learning!"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default SignupForm;
