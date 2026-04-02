/**
 * Consolidated User Onboarding Flow - Single Page
 * 
 * Single page with:
 * 1. Title: "LETS GET TO KNOW WHERE YOU STAND"
 * 2. Real-time checklist showing status
 * 3. Missing info form (if needed)
 * 4. Loading state before assessment
 */
import React, { useState, useEffect } from 'react';
import { useHistory } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiUtils } from '../../lib/api-utils';
import BackgroundShapes from '../background-shapes/BackgroundShapes';
import TeachrLogo from '../landing/TeachrLogo';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { detectLocationFromIP } from '../../lib/geolocation';
import { getCountryList, findMatchingCountryName } from '../../lib/countries';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import './auth.scss';

const AUTH_API_URL = import.meta.env.VITE_AUTH_SERVICE_URL || 'http://localhost:8003';
const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

const LANGUAGES = ["English", "Hindi", "Spanish", "French"];
const COUNTRIES = getCountryList();

interface CompletenessCheck {
  is_complete: boolean;
  missing_fields: string[];
  assessment_completed: boolean;
  assessment_subject: string;
  readiness_status: 'ready' | 'needs_info' | 'needs_assessment' | 'complete';
  user_data: {
    date_of_birth?: string;
    preferred_language?: string;
    location?: string;
    age?: number;
    current_grade?: string;
  };
}

type OnboardingStep = 'checking' | 'collecting_info' | 'starting_assessment' | 'ready';

const UserOnboardingFlow: React.FC = () => {
  const history = useHistory();
  const { isAuthenticated, isLoading } = useAuth();
  const [step, setStep] = useState<OnboardingStep>('checking');
  const [completeness, setCompleteness] = useState<CompletenessCheck | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [countrySearch, setCountrySearch] = useState('');
  const [loadingDots, setLoadingDots] = useState('');
  const [locationError, setLocationError] = useState(false);

  // Checklist status - updates in real-time
  const [checklistStatus, setChecklistStatus] = useState({
    age: false,
    learningLevel: false,
    region: false
  });
  const [checklistVisible, setChecklistVisible] = useState(false);

  // Update checklist when completeness data changes - with staggered animation
  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];
    if (completeness) {
      // First show checklist container
      setChecklistVisible(true);

      // Then update items one by one with delays
      timers.push(setTimeout(() => {
        setChecklistStatus(prev => ({
          ...prev,
          age: !!completeness.user_data.date_of_birth || !!completeness.user_data.age
        }));
      }, 500));

      timers.push(setTimeout(() => {
        setChecklistStatus(prev => ({
          ...prev,
          learningLevel: !!completeness.user_data.current_grade
        }));
      }, 1000));

      timers.push(setTimeout(() => {
        setChecklistStatus(prev => ({
          ...prev,
          // Region check passes if location exists OR if on localhost AND geolocation did not error
          region: !!completeness.user_data.location ||
            (window.location.hostname === 'localhost' && !locationError)
        }));
      }, 1500));
    }
    return () => { timers.forEach(clearTimeout); };
  }, [completeness, locationError]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      history.replace('/app/login');
      return;
    }

    if (isAuthenticated && !isLoading) {
      startOnboardingFlow();
    }
  }, [isAuthenticated, isLoading, history]);

  // Loading dots animation - slower animation
  useEffect(() => {
    if (step === 'starting_assessment') {
      let dotCount = 0;
      const interval = setInterval(() => {
        dotCount = (dotCount % 3) + 1;
        setLoadingDots('.'.repeat(dotCount));
      }, 800); // Slower animation (was 500ms)
      return () => clearInterval(interval);
    }
  }, [step]);

  const startOnboardingFlow = async () => {
    try {
      setStep('checking');

      // Check completeness
      const response = await apiUtils.get(`${AUTH_API_URL}/auth/check-completeness`);
      
      if (!response.ok) {
        throw new Error('Failed to check completeness');
      }

      const data: CompletenessCheck = await response.json();
      setCompleteness(data);

      // Longer delay to show checklist animation - let users see the status
      await new Promise(resolve => setTimeout(resolve, 3000));

      // Route based on readiness
      if (data.readiness_status === 'needs_info') {
        setStep('collecting_info');
      } else if (data.readiness_status === 'needs_assessment') {
        setStep('starting_assessment');
        // Longer loading time before redirecting to assessment
        await new Promise(resolve => setTimeout(resolve, 4000));
        
        window.dispatchEvent(new CustomEvent('onboarding-complete'));
        sessionStorage.setItem('onboarding_complete', 'true');
        history.replace(`/app/assessment/${data.assessment_subject}`);
      } else if (data.readiness_status === 'complete') {
        window.dispatchEvent(new CustomEvent('onboarding-complete'));
        sessionStorage.setItem('onboarding_complete', 'true');
        history.replace('/app');
      }
    } catch (error) {
      console.error('Error in onboarding flow:', error);
      // Don't mark onboarding as complete on error — retry instead so the user
      // actually fills in age/DOB and other required fields (Bug: age not asked).
      setStep('collecting_info');
      // Build a fallback completeness so the form shows all fields
      setCompleteness({
        is_complete: false,
        missing_fields: ['date_of_birth', 'preferred_language', 'location'],
        assessment_completed: false,
        assessment_subject: 'math',
        readiness_status: 'needs_info',
        user_data: {}
      });
    }
  };

  // Build schema based on missing fields
  const schemaFields: any = {};
  if (completeness?.missing_fields.includes('date_of_birth')) {
    schemaFields.dateOfBirth = z.string().min(1, "Date of birth is required");
  }
  if (completeness?.missing_fields.includes('preferred_language')) {
    schemaFields.preferredLanguage = z.string().min(1, "Please select your preferred language");
  }
  if (completeness?.missing_fields.includes('location')) {
    schemaFields.location = z.string().min(1, "Please select your location");
  }

  const schema = z.object(schemaFields);
  type FormData = z.infer<typeof schema>;

  const { control, handleSubmit, setValue, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema) as any,
    defaultValues: {
      dateOfBirth: completeness?.user_data.date_of_birth || '',
      preferredLanguage: completeness?.user_data.preferred_language || '',
      location: completeness?.user_data.location || '',
    },
  });

  // Re-initialize form when completeness loads so schema fields and defaultValues are
  // based on the actual missing_fields list (not the empty-schema from the initial render).
  useEffect(() => {
    if (completeness) {
      reset({
        dateOfBirth: completeness.user_data.date_of_birth || '',
        preferredLanguage: completeness.user_data.preferred_language || '',
        location: completeness.user_data.location || '',
      });
    }
  }, [completeness, reset]);

  // Auto-detect location if missing
  useEffect(() => {
    if (completeness?.missing_fields.includes('location') && !completeness?.user_data.location) {
      detectLocationFromIP().then((data) => {
        if (data.country) {
          const matchedCountry = findMatchingCountryName(data.country);
          if (matchedCountry) {
            setValue("location", matchedCountry);
          }
        }
      }).catch((err) => {
        console.error('Error detecting location:', err);
        setLocationError(true);
      });
    }
  }, [completeness?.missing_fields, completeness?.user_data.location, setValue]);

  const filteredCountries = React.useMemo(() => {
    if (!countrySearch.trim()) return COUNTRIES;
    const searchLower = countrySearch.toLowerCase();
    return COUNTRIES.filter(country => 
      country.name.toLowerCase().includes(searchLower)
    );
  }, [countrySearch]);

  const handleInfoSubmitted = async (formData: FormData) => {
    setIsSubmitting(true);
    setSubmitError('');
    
    try {
      const submitData: any = {};
      if (formData.dateOfBirth) {
        submitData.date_of_birth = formData.dateOfBirth;
      }
      if (formData.preferredLanguage) {
        submitData.preferred_language = formData.preferredLanguage;
      }
      if (formData.location) {
        submitData.location = formData.location;
      }

      const response = await apiUtils.post(
        `${AUTH_API_URL}/auth/update-missing-info`,
        submitData
      );

      if (!response.ok) {
        let detail = '';
        try {
          const errData = await response.json();
          detail = errData.detail || errData.message || errData.error || '';
        } catch { /* non-JSON error body */ }
        throw new Error(
          detail
            ? `Could not save your info: ${detail}`
            : `Could not save your info (HTTP ${response.status}). Please check your connection and try again.`
        );
      }

      // Re-check completeness to update checklist
      const recheckResponse = await apiUtils.get(`${AUTH_API_URL}/auth/check-completeness`);
      if (recheckResponse.ok) {
        const updatedData: CompletenessCheck = await recheckResponse.json();
        setCompleteness(updatedData);
      }

      // Move to starting assessment
      setStep('starting_assessment');
      
      // Longer loading time before redirecting
      await new Promise(resolve => setTimeout(resolve, 4000));

      window.dispatchEvent(new CustomEvent('onboarding-complete'));
      sessionStorage.setItem('onboarding_complete', 'true');

      if (completeness && !completeness.assessment_completed) {
        history.replace(`/app/assessment/${completeness.assessment_subject}`);
      } else {
        history.replace('/app');
      }
    } catch (error: any) {
      setSubmitError(error.message || 'Failed to save information');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-container">
      <BackgroundShapes />
      <div style={{
        padding: '40px 20px',
        textAlign: 'center',
        maxWidth: '700px',
        width: '100%',
        margin: '0 auto',
        minHeight: 'auto',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'flex-start',
        position: 'relative',
        zIndex: 1
      }}>
        {/* Branding */}
        <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'center' }}>
          <TeachrLogo size="large" />
        </div>

        {/* Main Card */}
        <div style={{
          border: '5px solid #000000',
          backgroundColor: '#FFFDF5',
          padding: '40px 32px',
          boxShadow: '4px 4px 0px 0px #000000',
          width: '100%',
          boxSizing: 'border-box' as const
        }}>
          {/* Title */}
          <h1 style={{
            fontSize: '32px',
            fontWeight: 900,
            marginBottom: '40px',
            color: '#000000',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            lineHeight: '1.2'
          }}>
            LET'S GET TO KNOW WHERE YOU STAND
          </h1>

          {/* Checklist - Always visible with animation */}
          <div style={{
            marginBottom: '40px',
            textAlign: 'left',
            display: 'flex',
            flexDirection: 'column',
            gap: '20px',
            padding: '24px',
            border: '4px solid #000000',
            backgroundColor: '#FFFFFF',
            boxShadow: '3px 3px 0 #000000',
            opacity: checklistVisible ? 1 : 0,
            transform: checklistVisible ? 'translateY(0)' : 'translateY(-10px)',
            transition: 'opacity 0.5s ease-out, transform 0.5s ease-out'
          }}>
            <ChecklistItem
              checked={checklistStatus.age}
              label="Checking your age"
            />
            <ChecklistItem
              checked={checklistStatus.learningLevel}
              label="Checking your learning level"
            />
            <ChecklistItem
              checked={checklistStatus.region}
              label="Checking your region"
            />
          </div>

          {/* Missing Info Section */}
          {step === 'collecting_info' && completeness && completeness.missing_fields.length > 0 && (
            <>
              <div style={{
                marginBottom: '32px',
                padding: '20px',
                border: '4px solid #000000',
                backgroundColor: '#FFD93D',
                boxShadow: '3px 3px 0 #000000'
              }}>
                <p style={{
                  fontSize: '18px',
                  fontWeight: 700,
                  color: '#000000',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  margin: 0
                }}>
                  Let's set up your profile
                </p>
              </div>

              <form method="post" onSubmit={handleSubmit(handleInfoSubmitted)}>
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '24px',
                  marginBottom: '24px'
                }}>
                  {submitError && (
                    <div style={{
                      padding: '16px 20px',
                      background: '#FF6B6B',
                      color: '#FFFFFF',
                      border: '4px solid #000000',
                      fontSize: '14px',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      boxShadow: '4px 4px 0px 0px #000000'
                    }}>
                      {submitError}
                    </div>
                  )}

                  {completeness.missing_fields.includes('date_of_birth') && (
                    <div>
                      <Label htmlFor="dateOfBirth" style={{ 
                        display: 'block', 
                        marginBottom: '12px', 
                        fontWeight: 700, 
                        fontSize: '14px',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        color: '#000000',
                        textAlign: 'left'
                      }}>
                        Date of Birth
                      </Label>
                      <Controller
                        name="dateOfBirth"
                        control={control}
                        render={({ field }) => (
                          <Input
                            {...field}
                            value={field.value as string ?? ''}
                            id="dateOfBirth"
                            type="date"
                            className="h-12 text-lg"
                            style={{
                              border: '4px solid #000000',
                              backgroundColor: '#FFFFFF',
                              fontWeight: 700,
                              boxShadow: '4px 4px 0px 0px #000000'
                            }}
                          />
                        )}
                      />
                      {errors.dateOfBirth && (
                        <p style={{ 
                          color: '#FF6B6B', 
                          fontSize: '14px', 
                          marginTop: '8px', 
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          letterSpacing: '0.05em',
                          textAlign: 'left'
                        }}>
                          {errors.dateOfBirth.message}
                        </p>
                      )}
                    </div>
                  )}

                  {completeness.missing_fields.includes('preferred_language') && (
                    <div>
                      <Label htmlFor="preferredLanguage" style={{ 
                        display: 'block', 
                        marginBottom: '12px', 
                        fontWeight: 700, 
                        fontSize: '14px',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        color: '#000000',
                        textAlign: 'left'
                      }}>
                        Please select your preferred language
                      </Label>
                      <Controller
                        name="preferredLanguage"
                        control={control}
                        render={({ field }) => (
                          <Select onValueChange={field.onChange} value={field.value as string}>
                            <SelectTrigger className="h-12 text-lg" style={{
                              border: '4px solid #000000',
                              backgroundColor: '#FFFFFF',
                              fontWeight: 700,
                              boxShadow: '4px 4px 0px 0px #000000'
                            }}>
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
                      {errors.preferredLanguage && (
                        <p style={{ 
                          color: '#FF6B6B', 
                          fontSize: '14px', 
                          marginTop: '8px', 
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          letterSpacing: '0.05em',
                          textAlign: 'left'
                        }}>
                          {errors.preferredLanguage.message}
                        </p>
                      )}
                    </div>
                  )}

                  {completeness.missing_fields.includes('location') && (
                    <div>
                      <Label htmlFor="location" style={{ 
                        display: 'block', 
                        marginBottom: '12px', 
                        fontWeight: 700, 
                        fontSize: '14px',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        color: '#000000',
                        textAlign: 'left'
                      }}>
                        Please select your region
                      </Label>
                      <p style={{ 
                        fontSize: '12px', 
                        color: 'rgba(0,0,0,0.6)', 
                        marginBottom: '12px',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        textAlign: 'left'
                      }}>
                        We'll customize content based on your location
                      </p>
                      <Controller
                        name="location"
                        control={control}
                        render={({ field }) => (
                          <Select onValueChange={(value) => { field.onChange(value); setCountrySearch(''); }} value={field.value as string}>
                            <SelectTrigger className="h-12 text-lg" style={{
                              border: '4px solid #000000',
                              backgroundColor: '#FFFFFF',
                              fontWeight: 700,
                              boxShadow: '4px 4px 0px 0px #000000'
                            }}>
                              <SelectValue placeholder="Select your country" />
                            </SelectTrigger>
                            <SelectContent className="max-h-[300px]">
                              <div className="sticky top-0 z-10 bg-popover p-2 border-b" onClick={(e) => e.stopPropagation()}>
                                <Input
                                  placeholder="Search countries..."
                                  value={countrySearch}
                                  onChange={(e) => setCountrySearch(e.target.value)}
                                  className="h-9"
                                  onClick={(e) => e.stopPropagation()}
                                  onKeyDown={(e) => e.stopPropagation()}
                                  style={{
                                    border: '3px solid #000000',
                                    backgroundColor: '#FFFFFF',
                                    fontWeight: 600
                                  }}
                                />
                              </div>
                              {filteredCountries.length === 0 ? (
                                <div className="px-2 py-4 text-sm text-muted-foreground text-center">
                                  No countries found
                                </div>
                              ) : (
                                filteredCountries.map((country) => (
                                  <SelectItem key={country.code} value={country.name}>
                                    {country.name}
                                  </SelectItem>
                                ))
                              )}
                            </SelectContent>
                          </Select>
                        )}
                      />
                      {errors.location && (
                        <p style={{ 
                          color: '#FF6B6B', 
                          fontSize: '14px', 
                          marginTop: '8px', 
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          letterSpacing: '0.05em',
                          textAlign: 'left'
                        }}>
                          {errors.location.message}
                        </p>
                      )}
                    </div>
                  )}

                  <Button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full h-12 text-base tracking-wide"
                    style={{
                      textTransform: 'uppercase',
                      fontWeight: 700,
                      marginTop: '8px',
                      border: '4px solid #000000',
                      backgroundColor: '#FFD93D',
                      color: '#000000',
                      boxShadow: '4px 4px 0px 0px #000000',
                      transition: 'all 100ms ease-out'
                    }}
                    onMouseDown={(e) => {
                      (e.target as HTMLElement).style.transform = 'translate(2px, 2px)';
                      (e.target as HTMLElement).style.boxShadow = '2px 2px 0px 0px #000000';
                    }}
                    onMouseUp={(e) => {
                      (e.target as HTMLElement).style.transform = 'translate(0, 0)';
                      (e.target as HTMLElement).style.boxShadow = '4px 4px 0px 0px #000000';
                    }}
                  >
                    {isSubmitting ? 'Saving...' : 'Continue'}
                  </Button>
                </div>
              </form>
            </>
          )}

          {/* Starting Assessment Loading */}
          {step === 'starting_assessment' && (
            <div style={{
              padding: '24px',
              border: '4px solid #000000',
              backgroundColor: '#FFD93D',
              boxShadow: '3px 3px 0 #000000'
            }}>
              <p style={{
                fontSize: '20px',
                fontWeight: 900,
                color: '#000000',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                margin: 0,
                fontFamily: 'system-ui, -apple-system, sans-serif'
              }}>
                Starting Assessment{loadingDots}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Checklist Item Component
const ChecklistItem: React.FC<{ checked: boolean; label: string }> = ({ checked, label }) => {
  const [isAnimating, setIsAnimating] = React.useState(false);

  React.useEffect(() => {
    if (checked) {
      setIsAnimating(true);
      const timer = setTimeout(() => setIsAnimating(false), 300);
      return () => clearTimeout(timer);
    }
  }, [checked]);

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      fontSize: '16px',
      fontWeight: 700,
      color: '#000000',
      textTransform: 'uppercase',
      letterSpacing: '0.05em'
    }}>
      <div style={{
        width: '28px',
        height: '28px',
        border: '3px solid #000000',
        backgroundColor: checked ? '#4ADE80' : '#FF6B6B',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        boxShadow: '2px 2px 0 #000000',
        transform: isAnimating ? 'scale(1.2)' : 'scale(1)',
        transition: 'all 0.3s ease-out'
      }}>
        {checked ? (
          <span style={{
            color: '#FFFFFF',
            fontSize: '20px',
            fontWeight: 900,
            lineHeight: 1
          }}>✓</span>
        ) : (
          <span style={{
            color: '#FFFFFF',
            fontSize: '20px',
            fontWeight: 900,
            lineHeight: 1
          }}>✗</span>
        )}
      </div>
      <span>{label}</span>
    </div>
  );
};

export default UserOnboardingFlow;
