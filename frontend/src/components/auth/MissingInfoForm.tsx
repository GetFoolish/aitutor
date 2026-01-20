/**
 * Missing Information Form Component
 * 
 * Neo-brutalist form for collecting missing user information.
 * Matches SignupForm design patterns exactly.
 * Dynamically shows only missing fields.
 */
import React, { useState, useEffect, useMemo } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { detectLocationFromIP } from '../../lib/geolocation';
import { getCountryList, findMatchingCountryName } from '../../lib/countries';
import BackgroundShapes from '../background-shapes/BackgroundShapes';
import './auth.scss';

const LANGUAGES = ["English", "Hindi", "Spanish", "French"];
const GENDERS = ["Male", "Female", "Other", "Prefer not to say"];
const COUNTRIES = getCountryList();

interface MissingInfoFormProps {
  missingFields: string[];
  existingData: {
    date_of_birth?: string;
    gender?: string;
    preferred_language?: string;
    location?: string;
  };
  onSubmit: (data: any) => void;
}

const MissingInfoForm: React.FC<MissingInfoFormProps> = ({
  missingFields,
  existingData,
  onSubmit
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [countrySearch, setCountrySearch] = useState('');

  // Build schema based on missing fields
  const schemaFields: any = {};
  if (missingFields.includes('date_of_birth')) {
    schemaFields.dateOfBirth = z.string().min(1, "Date of birth is required");
  }
  if (missingFields.includes('gender')) {
    schemaFields.gender = z.string().min(1, "Please select your gender");
  }
  if (missingFields.includes('preferred_language')) {
    schemaFields.preferredLanguage = z.string().min(1, "Please select your preferred language");
  }
  if (missingFields.includes('location')) {
    schemaFields.location = z.string().min(1, "Please select your location");
  }

  const schema = z.object(schemaFields);
  type FormData = z.infer<typeof schema>;

  const { control, handleSubmit, setValue, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema) as any,
    defaultValues: {
      dateOfBirth: existingData.date_of_birth || '',
      gender: existingData.gender || '',
      preferredLanguage: existingData.preferred_language || '',
      location: existingData.location || '',
    },
  });

  // Auto-detect location if missing
  useEffect(() => {
    if (missingFields.includes('location') && !existingData.location) {
      detectLocationFromIP().then((data) => {
        if (data.country) {
          const matchedCountry = findMatchingCountryName(data.country);
          if (matchedCountry) {
            setValue("location", matchedCountry);
          }
        }
      });
    }
  }, [missingFields, existingData.location, setValue]);

  const filteredCountries = useMemo(() => {
    if (!countrySearch.trim()) return COUNTRIES;
    const searchLower = countrySearch.toLowerCase();
    return COUNTRIES.filter(country => 
      country.name.toLowerCase().includes(searchLower)
    );
  }, [countrySearch]);

  const onSubmitForm = async (data: FormData) => {
    setIsSubmitting(true);
    setSubmitError('');
    
    try {
      const submitData: any = {};
      if (data.dateOfBirth) {
        submitData.date_of_birth = data.dateOfBirth;
      }
      if (data.gender) {
        submitData.gender = data.gender;
      }
      if (data.preferredLanguage) {
        submitData.preferred_language = data.preferredLanguage;
      }
      if (data.location) {
        submitData.location = data.location;
      }
      
      await onSubmit(submitData);
    } catch (error: any) {
      setSubmitError(error.message || 'Failed to save information');
      setIsSubmitting(false);
    }
  };

  // Build question text based on missing fields
  const getQuestionText = () => {
    if (missingFields.includes('date_of_birth') && missingFields.length === 1) {
      return "How old are you?";
    }
    if (missingFields.length === 1) {
      const field = missingFields[0];
      if (field === 'gender') return "What's your gender?";
      if (field === 'preferred_language') return "What language are you most comfortable in?";
      if (field === 'location') return "Where do you live?";
    }
    return "Before starting, I need some more information from you";
  };

  return (
    <div className="auth-container">
      <BackgroundShapes />
      <div style={{
        padding: '40px 20px',
        textAlign: 'center',
        maxWidth: '600px',
        margin: '0 auto',
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        position: 'relative',
        zIndex: 1
      }}>
        {/* Header Card - Neo-brutalist style */}
        <div style={{
          border: '5px solid var(--neo-black, #000000)',
          backgroundColor: 'var(--neo-yellow, #FFD93D)',
          padding: '32px',
          marginBottom: '32px',
          boxShadow: '3px 3px 0 var(--neo-black, #000000)'
        }}>
          <h1 style={{
            fontSize: '28px',
            fontWeight: 700,
            marginBottom: '16px',
            color: 'var(--neo-black, #000000)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            margin: 0
          }}>
            {getQuestionText()}
          </h1>
          <p style={{
            fontSize: '14px',
            color: 'var(--neo-black, #000000)',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            margin: 0,
            opacity: 0.8
          }}>
            This will help us personalize your learning experience
          </p>
        </div>

        {/* Form Card - Neo-brutalist style */}
        <form onSubmit={handleSubmit(onSubmitForm)}>
          <div style={{
            border: '5px solid var(--neo-black, #000000)',
            backgroundColor: 'var(--neo-bg, #FFFDF5)',
            padding: '32px',
            boxShadow: '3px 3px 0 var(--neo-black, #000000)',
            display: 'flex',
            flexDirection: 'column',
            gap: '24px'
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

            {missingFields.includes('date_of_birth') && (
              <div>
                <Label htmlFor="dateOfBirth" style={{ 
                  display: 'block', 
                  marginBottom: '12px', 
                  fontWeight: 700, 
                  fontSize: '14px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: 'var(--neo-black, #000000)'
                }}>
                  What's your date of birth?
                </Label>
                <Controller
                  name="dateOfBirth"
                  control={control}
                  render={({ field }) => (
                    <Input
                      {...field}
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
                    letterSpacing: '0.05em'
                  }}>
                    {errors.dateOfBirth.message}
                  </p>
                )}
              </div>
            )}

            {missingFields.includes('gender') && (
              <div>
                <Label htmlFor="gender" style={{ 
                  display: 'block', 
                  marginBottom: '12px', 
                  fontWeight: 700, 
                  fontSize: '14px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: 'var(--neo-black, #000000)'
                }}>
                  What's your gender?
                </Label>
                <Controller
                  name="gender"
                  control={control}
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value}>
                      <SelectTrigger className="h-12 text-lg" style={{
                        border: '4px solid #000000',
                        backgroundColor: '#FFFFFF',
                        fontWeight: 700,
                        boxShadow: '4px 4px 0px 0px #000000'
                      }}>
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
                {errors.gender && (
                  <p style={{ 
                    color: '#FF6B6B', 
                    fontSize: '14px', 
                    marginTop: '8px', 
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                  }}>
                    {errors.gender.message}
                  </p>
                )}
              </div>
            )}

            {missingFields.includes('preferred_language') && (
              <div>
                <Label htmlFor="preferredLanguage" style={{ 
                  display: 'block', 
                  marginBottom: '12px', 
                  fontWeight: 700, 
                  fontSize: '14px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: 'var(--neo-black, #000000)'
                }}>
                  What language are you most comfortable in?
                </Label>
                <Controller
                  name="preferredLanguage"
                  control={control}
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value}>
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
                    letterSpacing: '0.05em'
                  }}>
                    {errors.preferredLanguage.message}
                  </p>
                )}
              </div>
            )}

            {missingFields.includes('location') && (
              <div>
                <Label htmlFor="location" style={{ 
                  display: 'block', 
                  marginBottom: '12px', 
                  fontWeight: 700, 
                  fontSize: '14px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: 'var(--neo-black, #000000)'
                }}>
                  Where do you live?
                </Label>
                <p style={{ 
                  fontSize: '12px', 
                  color: 'rgba(0,0,0,0.6)', 
                  marginBottom: '12px',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em'
                }}>
                  We'll customize content based on your location
                </p>
                <Controller
                  name="location"
                  control={control}
                  render={({ field }) => (
                    <Select onValueChange={(value) => { field.onChange(value); setCountrySearch(''); }} value={field.value}>
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
                    letterSpacing: '0.05em'
                  }}>
                    {errors.location.message}
                  </p>
                )}
              </div>
            )}

            <Button
              type="submit"
              disabled={isSubmitting}
              className="w-full h-12 text-base"
              style={{
                textTransform: 'uppercase',
                fontWeight: 700,
                letterSpacing: '0.05em',
                marginTop: '8px',
                border: '4px solid #000000',
                backgroundColor: '#FF6B6B',
                color: '#FFFFFF',
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
      </div>
    </div>
  );
};

export default MissingInfoForm;
