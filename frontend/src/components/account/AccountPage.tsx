import React, { useEffect, useState } from 'react';
import { useHistory } from 'react-router-dom';
import { authAPI, AccountInfo } from '../../lib/auth-api';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { Input } from '../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import cn from 'classnames';
import { User, MapPin, Calendar, Clock, Loader2, Edit2, Save, X } from 'lucide-react';
import { getCountryList } from '../../lib/countries';
import Header from '../header/Header';

const LANGUAGES = ["English", "Hindi", "Spanish", "French"];
const GENDERS = ["Male", "Female", "Other", "Prefer not to say"];
const COUNTRIES = getCountryList();

const AccountPage: React.FC = () => {
  const history = useHistory();
  const [accountInfo, setAccountInfo] = useState<AccountInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    dateOfBirth: '',
    location: '',
    gender: '',
    preferredLanguage: '',
  });

  useEffect(() => {
    const fetchAccountInfo = async () => {
      try {
        setLoading(true);
        setError(null);
        const info = await authAPI.getAccountInfo();
        setAccountInfo(info);
        // Initialize form data
        setFormData({
          name: info.name || '',
          dateOfBirth: info.date_of_birth || '',
          location: info.location || '',
          gender: info.gender || '',
          preferredLanguage: info.preferred_language || '',
        });
      } catch (err: any) {
        console.error('Failed to fetch account info:', err);
        setError(err?.message || 'Failed to load account information');
      } finally {
        setLoading(false);
      }
    };

    fetchAccountInfo();
  }, []);

  const formatDate = (dateString: string) => {
    if (!dateString) return 'Not set';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    } catch {
      return dateString;
    }
  };

  const formatMinutes = (totalMinutes: number) => {
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    if (hours === 0) {
      return `${minutes} minutes`;
    }
    if (minutes === 0) {
      return `${hours} hour${hours > 1 ? 's' : ''}`;
    }
    return `${hours} hour${hours > 1 ? 's' : ''} ${minutes} minute${minutes > 1 ? 's' : ''}`;
  };

  const getPlanDisplayName = (plan: string | null | undefined): string => {
    if (!plan) return 'No Plan';
    const planNames: { [key: string]: string } = {
      'starter': 'Starter Plan',
      'pro': 'Pro Plan',
      'premium': 'Premium Plan'
    };
    return planNames[plan.toLowerCase()] || plan;
  };

  const handleBuyMinutes = () => {
    history.push('/pricing');
  };

  const handleEdit = () => {
    setIsEditing(true);
  };

  const handleCancel = () => {
    if (accountInfo) {
      setFormData({
        name: accountInfo.name || '',
        dateOfBirth: accountInfo.date_of_birth || '',
        location: accountInfo.location || '',
        gender: accountInfo.gender || '',
        preferredLanguage: accountInfo.preferred_language || '',
      });
    }
    setIsEditing(false);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      
      const updatedInfo = await authAPI.updateAccountInfo({
        name: formData.name,
        dateOfBirth: formData.dateOfBirth,
        location: formData.location,
        gender: formData.gender,
        preferredLanguage: formData.preferredLanguage,
      });
      
      setAccountInfo(updatedInfo);
      setIsEditing(false);
    } catch (err: any) {
      console.error('Failed to update account info:', err);
      setError(err?.message || 'Failed to update account information');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <>
        <Header sidebarOpen={false} onToggleSidebar={() => history.push('/')} hideSidebarToggle={true} />
        <div className="min-h-screen bg-[#FFFDF5] dark:bg-[#000000] p-4 md:p-8 pt-[60px] md:pt-[64px] lg:pt-[68px] page-transition">
          <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
            <Card className={cn(
              "border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]"
            )}>
              <CardHeader>
                <Skeleton className="h-6 w-32" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-full mb-4" />
                <Skeleton className="h-4 w-full mb-4" />
                <Skeleton className="h-4 w-3/4" />
              </CardContent>
            </Card>
            <Card className={cn(
              "border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]"
            )}>
              <CardHeader>
                <Skeleton className="h-6 w-32" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-12 w-full mb-4" />
                <Skeleton className="h-10 w-32" />
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
      </>
    );
  }

  if (error && !isEditing) {
    return (
      <>
        <Header sidebarOpen={false} onToggleSidebar={() => history.push('/')} hideSidebarToggle={true} />
        <div className="min-h-screen bg-[#FFFDF5] dark:bg-[#000000] p-4 md:p-8 pt-[60px] md:pt-[64px] lg:pt-[68px] flex items-center justify-center page-transition">
          <Card className={cn(
            "border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] max-w-md"
          )}>
            <CardContent className="pt-6">
              <p className="text-center text-red-600 dark:text-red-400 font-bold">{error}</p>
            </CardContent>
          </Card>
        </div>
      </>
    );
  }

  if (!accountInfo) {
    return null;
  }

  return (
    <>
      <Header sidebarOpen={false} onToggleSidebar={() => history.push('/')} hideSidebarToggle={true} />
      <div className="min-h-screen bg-[#FFFDF5] dark:bg-[#000000] p-4 md:p-8 pt-[60px] md:pt-[64px] lg:pt-[68px] page-transition">
      <div className="max-w-6xl mx-auto content-transition">
        <h1 className={cn(
          "text-3xl md:text-4xl font-black mb-6 md:mb-8 text-black dark:text-white uppercase tracking-wide",
          "border-b-[3px] border-black dark:border-white pb-4"
        )}>
          Account
        </h1>

        {error && isEditing && (
          <div className={cn(
            "mb-4 p-4 border-[2px] border-red-600 bg-red-50 dark:bg-red-900/20",
            "text-red-600 dark:text-red-400 font-bold"
          )}>
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
          {/* Personal Information Card */}
          <Card className={cn(
            "border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]",
            "shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]"
          )}>
            <CardHeader className={cn(
              "border-b-[2px] border-black dark:border-white bg-[#FFD93D]",
              "flex flex-row items-center justify-between"
            )}>
              <CardTitle className={cn(
                "text-xl font-black text-black uppercase flex items-center gap-2"
              )}>
                <User className="w-5 h-5" />
                Personal Information
              </CardTitle>
              {!isEditing && (
                <Button
                  onClick={handleEdit}
                  className={cn(
                    "h-8 px-3 font-black text-black transition-all transform",
                    "border-[2px] border-black shadow-[1px_1px_0_0_rgba(0,0,0,1)]",
                    "active:translate-x-0.5 active:translate-y-0.5 active:shadow-none",
                    "bg-[#FFFDF5] hover:bg-[#FFFDF5] uppercase text-xs"
                  )}
                >
                  <Edit2 className="w-3 h-3 mr-1" />
                  Edit
                </Button>
              )}
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              {/* Name */}
              <div>
                <label className={cn(
                  "text-xs font-black uppercase tracking-wide text-black dark:text-white mb-1 block"
                )}>
                  Name
                </label>
                {isEditing ? (
                  <Input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className={cn(
                      "h-10 text-base font-bold border-[2px] border-black dark:border-white",
                      "bg-[#FFFDF5] dark:bg-[#000000]"
                    )}
                  />
                ) : (
                  <p className={cn(
                    "text-base font-bold text-black dark:text-white p-2",
                    "border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]"
                  )}>
                    {accountInfo.name || 'Not set'}
                  </p>
                )}
              </div>

              {/* Email (read-only) */}
              <div>
                <label className={cn(
                  "text-xs font-black uppercase tracking-wide text-black dark:text-white mb-1 block"
                )}>
                  Email
                </label>
                <p className={cn(
                  "text-base font-bold text-black dark:text-white p-2",
                  "border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]"
                )}>
                  {accountInfo.email || 'Not set'}
                </p>
              </div>

              {/* Date of Birth */}
              <div>
                <label className={cn(
                  "text-xs font-black uppercase tracking-wide text-black dark:text-white mb-1 block flex items-center gap-1"
                )}>
                  <Calendar className="w-3 h-3" />
                  Date of Birth
                </label>
                {isEditing ? (
                  <Input
                    type="date"
                    value={formData.dateOfBirth}
                    onChange={(e) => setFormData({ ...formData, dateOfBirth: e.target.value })}
                    className={cn(
                      "h-10 text-base font-bold border-[2px] border-black dark:border-white",
                      "bg-[#FFFDF5] dark:bg-[#000000]"
                    )}
                  />
                ) : (
                  <p className={cn(
                    "text-base font-bold text-black dark:text-white p-2",
                    "border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]"
                  )}>
                    {formatDate(accountInfo.date_of_birth)}
                  </p>
                )}
              </div>

              {/* Location */}
              <div>
                <label className={cn(
                  "text-xs font-black uppercase tracking-wide text-black dark:text-white mb-1 block flex items-center gap-1"
                )}>
                  <MapPin className="w-3 h-3" />
                  Location
                </label>
                {isEditing ? (
                  <Select
                    value={formData.location}
                    onValueChange={(value) => setFormData({ ...formData, location: value })}
                  >
                    <SelectTrigger className={cn(
                      "h-10 text-base font-bold border-[2px] border-black dark:border-white",
                      "bg-[#FFFDF5] dark:bg-[#000000]"
                    )}>
                      <SelectValue placeholder="Select country" />
                    </SelectTrigger>
                    <SelectContent className="max-h-[300px]">
                      {COUNTRIES.map((country) => (
                        <SelectItem key={country.code} value={country.name}>
                          {country.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <p className={cn(
                    "text-base font-bold text-black dark:text-white p-2",
                    "border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]"
                  )}>
                    {accountInfo.location || 'Not set'}
                  </p>
                )}
              </div>

              {/* Gender */}
              <div>
                <label className={cn(
                  "text-xs font-black uppercase tracking-wide text-black dark:text-white mb-1 block"
                )}>
                  Gender
                </label>
                {isEditing ? (
                  <Select
                    value={formData.gender}
                    onValueChange={(value) => setFormData({ ...formData, gender: value })}
                  >
                    <SelectTrigger className={cn(
                      "h-10 text-base font-bold border-[2px] border-black dark:border-white",
                      "bg-[#FFFDF5] dark:bg-[#000000]"
                    )}>
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
                ) : (
                  <p className={cn(
                    "text-base font-bold text-black dark:text-white p-2",
                    "border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]"
                  )}>
                    {accountInfo.gender || 'Not set'}
                  </p>
                )}
              </div>

              {/* Preferred Language */}
              <div>
                <label className={cn(
                  "text-xs font-black uppercase tracking-wide text-black dark:text-white mb-1 block"
                )}>
                  Preferred Language
                </label>
                {isEditing ? (
                  <Select
                    value={formData.preferredLanguage}
                    onValueChange={(value) => setFormData({ ...formData, preferredLanguage: value })}
                  >
                    <SelectTrigger className={cn(
                      "h-10 text-base font-bold border-[2px] border-black dark:border-white",
                      "bg-[#FFFDF5] dark:bg-[#000000]"
                    )}>
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
                ) : (
                  <p className={cn(
                    "text-base font-bold text-black dark:text-white p-2",
                    "border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]"
                  )}>
                    {accountInfo.preferred_language || 'Not set'}
                  </p>
                )}
              </div>

              {/* User Type (read-only) */}
              <div>
                <label className={cn(
                  "text-xs font-black uppercase tracking-wide text-black dark:text-white mb-1 block"
                )}>
                  User Type
                </label>
                <p className={cn(
                  "text-base font-bold text-black dark:text-white p-2",
                  "border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]"
                )}>
                  {accountInfo.user_type ? accountInfo.user_type.charAt(0).toUpperCase() + accountInfo.user_type.slice(1) : 'Student'}
                </p>
              </div>

              {/* Edit buttons */}
              {isEditing && (
                <div className="flex gap-2 pt-2">
                  <Button
                    onClick={handleSave}
                    disabled={saving}
                    className={cn(
                      "flex-1 py-2 font-black text-black transition-all transform",
                      "border-[2px] border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)]",
                      "active:translate-x-1 active:translate-y-1 active:shadow-none",
                      "bg-[#FFD93D] hover:bg-[#FFD93D] uppercase"
                    )}
                  >
                    {saving ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4 mr-2" />
                        Save
                      </>
                    )}
                  </Button>
                  <Button
                    onClick={handleCancel}
                    disabled={saving}
                    className={cn(
                      "flex-1 py-2 font-black text-black transition-all transform",
                      "border-[2px] border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)]",
                      "active:translate-x-1 active:translate-y-1 active:shadow-none",
                      "bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FFFDF5] dark:hover:bg-[#000000] uppercase"
                    )}
                  >
                    <X className="w-4 h-4 mr-2" />
                    Cancel
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Minutes Card */}
          <Card className={cn(
            "border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]",
            "shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]"
          )}>
            <CardHeader className={cn(
              "border-b-[2px] border-black dark:border-white bg-[#C4B5FD]"
            )}>
              <CardTitle className={cn(
                "text-xl font-black text-black uppercase flex items-center gap-2"
              )}>
                <Clock className="w-5 h-5" />
                Minutes
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              <div>
                <label className={cn(
                  "text-xs font-black uppercase tracking-wide text-black dark:text-white mb-1 block"
                )}>
                  Subscription Plan
                </label>
                <p className={cn(
                  "text-base font-bold text-black dark:text-white p-2",
                  "border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]"
                )}>
                  {getPlanDisplayName(accountInfo.subscription_plan)}
                </p>
                
                {accountInfo.subscription_plan && (
                  <p className={cn(
                    "text-xs font-bold text-gray-600 dark:text-gray-400 mt-2 p-2",
                    "border-[2px] border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 rounded"
                  )}>
                    ℹ️ Your subscription renews monthly. Balance resets to plan minutes each month.
                  </p>
                )}
              </div>

              <div>
                <label className={cn(
                  "text-xs font-black uppercase tracking-wide text-black dark:text-white mb-1 block"
                )}>
                  Balance
                </label>
                <p className={cn(
                  "text-3xl font-black text-black dark:text-white p-4",
                  "border-[2px] border-black dark:border-white bg-[#FFD93D]"
                )}>
                  {formatMinutes((accountInfo.credits?.balance || 0) + (accountInfo.free_minutes?.balance || 0))}
                </p>

                {/* Reset Timer - Show when user has 0 minutes and reset info is available */}
                {((accountInfo.credits?.balance || 0) + (accountInfo.free_minutes?.balance || 0)) === 0 &&
                 accountInfo.free_minutes?.next_reset_in_hours !== undefined &&
                 accountInfo.free_minutes?.next_reset_in_hours !== null && (
                  <div className={cn(
                    "mt-2 p-2 text-xs font-bold",
                    "border-[2px] border-black dark:border-white bg-[#C4B5FD] text-black"
                  )}>
                    {accountInfo.free_minutes.next_reset_in_hours === 0 && accountInfo.free_minutes.next_reset_in_minutes === 0 ? (
                      <>
                        ✨ Free minutes available now! <span className="font-black">Refresh the page</span> to get your 15 free minutes.
                      </>
                    ) : accountInfo.free_minutes.next_reset_in_hours !== null && accountInfo.free_minutes.next_reset_in_minutes !== null ? (
                      <>
                        ⏱️ Free minutes reset in{' '}
                        <span className="font-black">
                          {accountInfo.free_minutes.next_reset_in_hours > 0 &&
                            `${accountInfo.free_minutes.next_reset_in_hours}h`}
                          {accountInfo.free_minutes.next_reset_in_hours > 0 &&
                           accountInfo.free_minutes.next_reset_in_minutes > 0 && ' '}
                          {accountInfo.free_minutes.next_reset_in_minutes > 0 &&
                            `${accountInfo.free_minutes.next_reset_in_minutes}m`}
                        </span>
                      </>
                    ) : null}
                  </div>
                )}
              </div>

              <Button
                onClick={handleBuyMinutes}
                className={cn(
                  "w-full py-3 font-black text-black transition-all transform",
                  "border-[2px] border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)]",
                  "active:translate-x-1 active:translate-y-1 active:shadow-none",
                  "bg-[#FFD93D] hover:bg-[#FFD93D] uppercase"
                )}
              >
                Buy Minutes
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
    </>
  );
};

export default AccountPage;
