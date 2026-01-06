import React, { useEffect, useState } from 'react';
import { authAPI, AccountInfo } from '../../lib/auth-api';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import cn from 'classnames';
import { User, MapPin, Calendar, DollarSign, Loader2 } from 'lucide-react';

const AccountPage: React.FC = () => {
  const [accountInfo, setAccountInfo] = useState<AccountInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAccountInfo = async () => {
      try {
        setLoading(true);
        setError(null);
        const info = await authAPI.getAccountInfo();
        setAccountInfo(info);
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

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
    }).format(amount);
  };

  const handleBuyCredits = () => {
    // Placeholder for Phase 4: Stripe integration
    alert('Buy Credits feature coming soon!');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FFFDF5] dark:bg-[#000000] p-4 md:p-8">
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
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#FFFDF5] dark:bg-[#000000] p-4 md:p-8 flex items-center justify-center">
        <Card className={cn(
          "border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] max-w-md"
        )}>
          <CardContent className="pt-6">
            <p className="text-center text-red-600 dark:text-red-400 font-bold">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!accountInfo) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#FFFDF5] dark:bg-[#000000] p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className={cn(
          "text-3xl md:text-4xl font-black mb-6 md:mb-8 text-black dark:text-white uppercase tracking-wide",
          "border-b-[3px] border-black dark:border-white pb-4"
        )}>
          Account
        </h1>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
          {/* Personal Information Card */}
          <Card className={cn(
            "border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]",
            "shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]"
          )}>
            <CardHeader className={cn(
              "border-b-[2px] border-black dark:border-white bg-[#FFD93D]"
            )}>
              <CardTitle className={cn(
                "text-xl font-black text-black uppercase flex items-center gap-2"
              )}>
                <User className="w-5 h-5" />
                Personal Information
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              <div>
                <label className={cn(
                  "text-xs font-black uppercase tracking-wide text-black dark:text-white mb-1 block"
                )}>
                  Name
                </label>
                <p className={cn(
                  "text-base font-bold text-black dark:text-white p-2",
                  "border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]"
                )}>
                  {accountInfo.name || 'Not set'}
                </p>
              </div>

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

              <div>
                <label className={cn(
                  "text-xs font-black uppercase tracking-wide text-black dark:text-white mb-1 block flex items-center gap-1"
                )}>
                  <Calendar className="w-3 h-3" />
                  Date of Birth
                </label>
                <p className={cn(
                  "text-base font-bold text-black dark:text-white p-2",
                  "border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]"
                )}>
                  {formatDate(accountInfo.date_of_birth)}
                </p>
              </div>

              <div>
                <label className={cn(
                  "text-xs font-black uppercase tracking-wide text-black dark:text-white mb-1 block flex items-center gap-1"
                )}>
                  <MapPin className="w-3 h-3" />
                  Location
                </label>
                <p className={cn(
                  "text-base font-bold text-black dark:text-white p-2",
                  "border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]"
                )}>
                  {accountInfo.location || 'Not set'}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Credits Card */}
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
                <DollarSign className="w-5 h-5" />
                Credits
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
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
                  {formatCurrency(accountInfo.credits.balance, accountInfo.credits.currency)}
                </p>
              </div>

              <Button
                onClick={handleBuyCredits}
                className={cn(
                  "w-full py-3 font-black text-black transition-all transform",
                  "border-[2px] border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)]",
                  "active:translate-x-1 active:translate-y-1 active:shadow-none",
                  "bg-[#FFD93D] hover:bg-[#FFD93D] uppercase"
                )}
              >
                Buy Credits
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default AccountPage;

