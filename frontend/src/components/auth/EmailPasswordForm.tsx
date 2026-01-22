/**
 * Email/Password authentication form - Login and Signup tabs
 */
import React, { useState, useEffect, useMemo } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { authAPI } from '../../lib/auth-api';
import { detectLocationFromIP } from '../../lib/geolocation';
import { getCountryList, findMatchingCountryName } from '../../lib/countries';
import SignupForm from './SignupForm';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Eye, EyeOff } from 'lucide-react';
import './auth.scss';

const LANGUAGES = ["English", "Hindi", "Spanish", "French"];
const GENDERS = ["Male", "Female", "Other", "Prefer not to say"];
const COUNTRIES = getCountryList();

// Login Schema
const loginSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(1, "Password is required"),
});

// Signup Schema
const signupSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Invalid email address"),
  password: z.string()
    .min(8, "Password must be at least 8 characters")
    .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
    .regex(/[a-z]/, "Password must contain at least one lowercase letter")
    .regex(/[0-9]/, "Password must contain at least one digit"),
  confirmPassword: z.string(),
  dateOfBirth: z.string().min(1, "Date of birth is required"),
  gender: z.string().min(1, "Please select your gender"),
  preferredLanguage: z.string().min(1, "Please select your preferred language"),
  location: z.string().min(1, "Please select your location"),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

type LoginFormData = z.infer<typeof loginSchema>;
type SignupFormData = z.infer<typeof signupSchema>;

interface EmailPasswordFormProps {
  onAuthSuccess: (token: string, user: any) => void;
}

const EmailPasswordForm: React.FC<EmailPasswordFormProps> = ({ onAuthSuccess }) => {
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [showSetupWizard, setShowSetupWizard] = useState(false);
  const [tempSignupData, setTempSignupData] = useState<any>(null);
  const [countrySearch, setCountrySearch] = useState('');

  const {
    control: loginControl,
    handleSubmit: handleLoginSubmit,
    formState: { errors: loginErrors },
    reset: resetLogin,
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema) as any,
    defaultValues: {
      email: '',
      password: '',
    },
  });

  const {
    control: signupControl,
    handleSubmit: handleSignupSubmit,
    formState: { errors: signupErrors },
    reset: resetSignup,
    setValue: setSignupValue,
  } = useForm<SignupFormData>({
    resolver: zodResolver(signupSchema) as any,
    defaultValues: {
      name: '',
      email: '',
      password: '',
      confirmPassword: '',
      dateOfBirth: '',
      gender: '',
      preferredLanguage: '',
      location: '',
    },
  });

  // Detect location when in signup mode
  useEffect(() => {
    if (mode === 'signup') {
      detectLocationFromIP().then((data) => {
        if (data.country) {
          // Try to match detected country name with country-list names
          const matchedCountry = findMatchingCountryName(data.country);
          if (matchedCountry) {
            setSignupValue("location", matchedCountry);
          }
        }
      });
    }
  }, [mode, setSignupValue]);

  // Filter countries based on search
  const filteredCountries = useMemo(() => {
    if (!countrySearch.trim()) {
      return COUNTRIES;
    }
    const searchLower = countrySearch.toLowerCase();
    return COUNTRIES.filter(country => 
      country.name.toLowerCase().includes(searchLower)
    );
  }, [countrySearch]);

  const onLogin = async (data: LoginFormData) => {
    setIsSubmitting(true);
    setSubmitError('');

    try {
      const response = await authAPI.emailLogin(data.email, data.password);
      onAuthSuccess(response.token, response.user);
    } catch (err: any) {
      setSubmitError(err.message || 'Login failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const onSignup = async (data: SignupFormData) => {
    setIsSubmitting(true);
    setSubmitError('');

    try {
      const response = await authAPI.emailSignup(
        data.email,
        data.password,
        data.name,
        data.dateOfBirth,
        data.gender,
        data.preferredLanguage,
        data.location
      );
      onAuthSuccess(response.token, response.user);
    } catch (err: any) {
      setSubmitError(err.message || 'Signup failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const switchMode = () => {
    setMode(mode === 'login' ? 'signup' : 'login');
    setSubmitError('');
    resetLogin();
    resetSignup();
  };

  return (
    <div style={{ width: '100%' }}>
      {/* Tab Buttons */}
      <div style={{
        display: 'flex',
        gap: '12px',
        marginBottom: '24px',
      }}>
        <button
          type="button"
          onClick={() => setMode('login')}
          style={{
            flex: 1,
            padding: '12px 16px',
            border: mode === 'login' ? '4px solid #000000' : '2px solid rgba(0,0,0,0.2)',
            background: mode === 'login' ? '#FFD93D' : 'transparent',
            fontWeight: 700,
            textTransform: 'uppercase',
            fontSize: '14px',
            cursor: 'pointer',
            boxShadow: mode === 'login' ? '4px 4px 0px 0px #000000' : 'none',
            transform: mode === 'login' ? 'translateY(-2px)' : 'none',
            transition: 'all 150ms ease',
          }}
        >
          Login
        </button>
        <button
          type="button"
          onClick={() => setMode('signup')}
          style={{
            flex: 1,
            padding: '12px 16px',
            border: mode === 'signup' ? '4px solid #000000' : '2px solid rgba(0,0,0,0.2)',
            background: mode === 'signup' ? '#FFD93D' : 'transparent',
            fontWeight: 700,
            textTransform: 'uppercase',
            fontSize: '14px',
            cursor: 'pointer',
            boxShadow: mode === 'signup' ? '4px 4px 0px 0px #000000' : 'none',
            transform: mode === 'signup' ? 'translateY(-2px)' : 'none',
            transition: 'all 150ms ease',
          }}
        >
          Sign Up
        </button>
      </div>

      {/* Login Form */}
      {mode === 'login' && (
        <form onSubmit={handleLoginSubmit(onLogin)}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <Label htmlFor="login-email" style={{ display: 'block', marginBottom: '8px', fontWeight: 700, fontSize: '14px' }}>
                Email
              </Label>
              <Controller
                name="email"
                control={loginControl}
                render={({ field }) => (
                  <Input
                    {...field}
                    id="login-email"
                    type="email"
                    placeholder="your@email.com"
                    className="h-12 text-lg"
                  />
                )}
              />
              {loginErrors.email && (
                <p style={{ color: '#FF6B6B', fontSize: '14px', marginTop: '4px', fontWeight: 600 }}>
                  {loginErrors.email.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="login-password" style={{ display: 'block', marginBottom: '8px', fontWeight: 700, fontSize: '14px' }}>
                Password
              </Label>
              <div style={{ position: 'relative' }}>
                <Controller
                  name="password"
                  control={loginControl}
                  render={({ field }) => (
                    <Input
                      {...field}
                      id="login-password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Enter password"
                      className="h-12 text-lg"
                    />
                  )}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '12px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    padding: '4px',
                  }}
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
              {loginErrors.password && (
                <p style={{ color: '#FF6B6B', fontSize: '14px', marginTop: '4px', fontWeight: 600 }}>
                  {loginErrors.password.message}
                </p>
              )}
            </div>

            {submitError && (
              <div style={{
                padding: '12px 16px',
                background: '#FF6B6B',
                color: 'white',
                border: '3px solid #000000',
                fontWeight: 600,
                fontSize: '14px',
              }}>
                {submitError}
              </div>
            )}

            <Button
              type="submit"
              disabled={isSubmitting}
              className="w-full h-12 text-base"
              style={{
                textTransform: 'uppercase',
                fontWeight: 700,
              }}
            >
              {isSubmitting ? 'Logging in...' : 'Login'}
            </Button>
          </div>
        </form>
      )}

      {/* Signup Form */}
      {mode === 'signup' && (
        <form onSubmit={handleSignupSubmit(onSignup)}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <Label htmlFor="signup-name" style={{ display: 'block', marginBottom: '8px', fontWeight: 700, fontSize: '14px' }}>
                Full Name
              </Label>
              <Controller
                name="name"
                control={signupControl}
                render={({ field }) => (
                  <Input
                    {...field}
                    id="signup-name"
                    type="text"
                    placeholder="Enter your name"
                    className="h-12 text-lg"
                  />
                )}
              />
              {signupErrors.name && (
                <p style={{ color: '#FF6B6B', fontSize: '14px', marginTop: '4px', fontWeight: 600 }}>
                  {signupErrors.name.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="signup-email" style={{ display: 'block', marginBottom: '8px', fontWeight: 700, fontSize: '14px' }}>
                Email
              </Label>
              <Controller
                name="email"
                control={signupControl}
                render={({ field }) => (
                  <Input
                    {...field}
                    id="signup-email"
                    type="email"
                    placeholder="your@email.com"
                    className="h-12 text-lg"
                  />
                )}
              />
              {signupErrors.email && (
                <p style={{ color: '#FF6B6B', fontSize: '14px', marginTop: '4px', fontWeight: 600 }}>
                  {signupErrors.email.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="signup-password" style={{ display: 'block', marginBottom: '8px', fontWeight: 700, fontSize: '14px' }}>
                Password
              </Label>
              <div style={{ position: 'relative' }}>
                <Controller
                  name="password"
                  control={signupControl}
                  render={({ field }) => (
                    <Input
                      {...field}
                      id="signup-password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Min 8 chars, 1 uppercase, 1 digit"
                      className="h-12 text-lg"
                    />
                  )}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '12px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    padding: '4px',
                  }}
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
              {signupErrors.password && (
                <p style={{ color: '#FF6B6B', fontSize: '14px', marginTop: '4px', fontWeight: 600 }}>
                  {signupErrors.password.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="signup-confirm" style={{ display: 'block', marginBottom: '8px', fontWeight: 700, fontSize: '14px' }}>
                Confirm Password
              </Label>
              <div style={{ position: 'relative' }}>
                <Controller
                  name="confirmPassword"
                  control={signupControl}
                  render={({ field }) => (
                    <Input
                      {...field}
                      id="signup-confirm"
                      type={showConfirmPassword ? 'text' : 'password'}
                      placeholder="Re-enter password"
                      className="h-12 text-lg"
                    />
                  )}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  style={{
                    position: 'absolute',
                    right: '12px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    padding: '4px',
                  }}
                >
                  {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
              {signupErrors.confirmPassword && (
                <p style={{ color: '#FF6B6B', fontSize: '14px', marginTop: '4px', fontWeight: 600 }}>
                  {signupErrors.confirmPassword.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="signup-dob" style={{ display: 'block', marginBottom: '8px', fontWeight: 700, fontSize: '14px' }}>
                Date of Birth
              </Label>
              <Controller
                name="dateOfBirth"
                control={signupControl}
                render={({ field }) => (
                  <Input
                    {...field}
                    id="signup-dob"
                    type="date"
                    className="h-12 text-lg"
                  />
                )}
              />
              {signupErrors.dateOfBirth && (
                <p style={{ color: '#FF6B6B', fontSize: '14px', marginTop: '4px', fontWeight: 600 }}>
                  {signupErrors.dateOfBirth.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="signup-gender" style={{ display: 'block', marginBottom: '8px', fontWeight: 700, fontSize: '14px' }}>
                Gender
              </Label>
              <Controller
                name="gender"
                control={signupControl}
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
              {signupErrors.gender && (
                <p style={{ color: '#FF6B6B', fontSize: '14px', marginTop: '4px', fontWeight: 600 }}>
                  {signupErrors.gender.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="signup-language" style={{ display: 'block', marginBottom: '8px', fontWeight: 700, fontSize: '14px' }}>
                Preferred Language
              </Label>
              <Controller
                name="preferredLanguage"
                control={signupControl}
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
              {signupErrors.preferredLanguage && (
                <p style={{ color: '#FF6B6B', fontSize: '14px', marginTop: '4px', fontWeight: 600 }}>
                  {signupErrors.preferredLanguage.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="signup-location" style={{ display: 'block', marginBottom: '8px', fontWeight: 700, fontSize: '14px' }}>
                Location (Country)
              </Label>
              <p style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>
                We'll customize content based on your location
              </p>
              <Controller
                name="location"
                control={signupControl}
                render={({ field }) => (
                  <Select onValueChange={(value) => { field.onChange(value); setCountrySearch(''); }} value={field.value}>
                    <SelectTrigger className="h-12 text-lg">
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
              {signupErrors.location && (
                <p style={{ color: '#FF6B6B', fontSize: '14px', marginTop: '4px', fontWeight: 600 }}>
                  {signupErrors.location.message}
                </p>
              )}
            </div>

            {submitError && (
              <div style={{
                padding: '12px 16px',
                background: '#FF6B6B',
                color: 'white',
                border: '3px solid #000000',
                fontWeight: 600,
                fontSize: '14px',
              }}>
                {submitError}
              </div>
            )}

            <Button
              type="submit"
              disabled={isSubmitting}
              className="w-full h-12 text-base"
              style={{
                textTransform: 'uppercase',
                fontWeight: 700,
              }}
            >
              {isSubmitting ? 'Creating Account...' : 'Create Account'}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
};

export default EmailPasswordForm;
