import React, { useState, useEffect } from 'react';
import { useHistory } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '../ui/card';
import { Button } from '../ui/button';
import cn from 'classnames';
import { Check, Star } from 'lucide-react';
import { Skeleton } from '../ui/skeleton';
import { paymentAPI } from '../../lib/payment-api';
import { authAPI } from '../../lib/auth-api';
import Header from '../header/Header';

interface PricingTier {
  name: string;
  price: string;
  description: string;
  features: string[];
  isPopular?: boolean;
  buttonText: string;
}

const pricingTiers: PricingTier[] = [
  {
    name: 'Starter',
    price: '$9.99',
    description: 'Perfect for getting started',
    features: [
      '5 hours of tutoring',
      'Basic question bank access',
      'Email support',
      'Progress tracking'
    ],
    buttonText: 'Select Plan'
  },
  {
    name: 'Pro',
    price: '$19.99',
    description: 'Most popular choice',
    features: [
      '20 hours of tutoring',
      'Full question bank access',
      'Priority email support',
      'Advanced progress tracking',
      'Learning analytics',
      'Custom study plans'
    ],
    isPopular: true,
    buttonText: 'Select Plan'
  },
  {
    name: 'Premium',
    price: '$39.99',
    description: 'For serious learners',
    features: [
      '50 hours of tutoring',
      'Full question bank access',
      '24/7 priority support',
      'Advanced progress tracking',
      'Detailed learning analytics',
      'Personalized study plans',
      'One-on-one sessions',
      'Early access to new features'
    ],
    buttonText: 'Select Plan'
  }
];

const PricingPage: React.FC = () => {
  const history = useHistory();
  const [isLoading, setIsLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [accountInfo, setAccountInfo] = useState<any>(null);
  const [loadingAccount, setLoadingAccount] = useState(true);
  const [initialLoading, setInitialLoading] = useState(true);

  useEffect(() => {
    const fetchAccountInfo = async () => {
      try {
        setLoadingAccount(true);
        const info = await authAPI.getAccountInfo();
        setAccountInfo(info);
      } catch (err) {
        console.error('Failed to fetch account info:', err);
      } finally {
        setLoadingAccount(false);
        setInitialLoading(false);
      }
    };

    fetchAccountInfo();
  }, []);

  const handleSelectPlan = async (tierName: string) => {
    try {
      setIsLoading(tierName);
      setError(null);

      const planMap: { [key: string]: 'starter' | 'pro' | 'premium' } = {
        'Starter': 'starter',
        'Pro': 'pro',
        'Premium': 'premium'
      };

      const plan = planMap[tierName];
      const session = await paymentAPI.createCheckoutSession(plan);

      // Redirect to Stripe checkout
      if (session.checkout_url) {
        window.location.href = session.checkout_url;
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create checkout session';
      setError(errorMessage);
      console.error('Checkout error:', err);
      
      // Show alert for better UX when user already has subscription
      if (errorMessage.includes('already have an active')) {
        alert(`${errorMessage}\n\nPlease visit your Account page to manage your subscription.`);
      }
    } finally {
      setIsLoading(null);
    }
  };

  // Helper to check if this is user's current plan
  const isCurrentPlan = (tierName: string): boolean => {
    if (!accountInfo?.subscription_plan) return false;
    
    const planMap: { [key: string]: string } = {
      'starter': 'Starter',
      'pro': 'Pro',
      'premium': 'Premium'
    };
    
    return planMap[accountInfo.subscription_plan.toLowerCase()] === tierName;
  };

  if (initialLoading) {
    return (
      <>
        <Header sidebarOpen={false} onToggleSidebar={() => history.push('/')} hideSidebarToggle={true} />
        <div className="min-h-screen bg-[#FFFDF5] dark:bg-[#000000] p-4 md:p-8 pt-[60px] md:pt-[64px] lg:pt-[68px] page-transition">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-8 md:mb-12">
              <Skeleton className="h-12 w-64 mx-auto mb-4" />
              <Skeleton className="h-6 w-96 mx-auto" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
              {[1, 2, 3].map((i) => (
                <Card
                  key={i}
                  className={cn(
                    "border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]",
                    "shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]"
                  )}
                >
                  <CardHeader className="border-b-[2px] border-black dark:border-white bg-[#FFD93D]">
                    <Skeleton className="h-8 w-32 mb-2" />
                    <Skeleton className="h-10 w-24" />
                  </CardHeader>
                  <CardContent className="pt-6">
                    <div className="space-y-3">
                      {[1, 2, 3, 4].map((j) => (
                        <Skeleton key={j} className="h-4 w-full" />
                      ))}
                    </div>
                  </CardContent>
                  <CardFooter>
                    <Skeleton className="h-12 w-full" />
                  </CardFooter>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <Header sidebarOpen={false} onToggleSidebar={() => history.push('/')} hideSidebarToggle={true} />
      <div className="min-h-screen bg-[#FFFDF5] dark:bg-[#000000] p-4 md:p-8 pt-[60px] md:pt-[64px] lg:pt-[68px] page-transition">
        <div className="max-w-7xl mx-auto content-transition">
        <div className="text-center mb-8 md:mb-12">
          <h1 className={cn(
            "text-4xl md:text-5xl font-black mb-4 text-black dark:text-white uppercase tracking-wide"
          )}>
            Pricing
          </h1>
          <p className={cn(
            "text-lg md:text-xl font-bold text-black dark:text-white"
          )}>
            Choose the plan that works for you
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
          {pricingTiers.map((tier) => (
            <Card
              key={tier.name}
              className={cn(
                "border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]",
                "shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]",
                "relative transition-all hover:shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:hover:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)]",
                tier.isPopular && "border-[4px] md:border-[5px]"
              )}
            >
              {tier.isPopular && (
                <div className={cn(
                  "absolute -top-4 left-1/2 transform -translate-x-1/2",
                  "px-4 py-1 border-[2px] border-black dark:border-white",
                  "bg-[#FFD93D] text-black font-black text-xs uppercase tracking-wide",
                  "flex items-center gap-1"
                )}>
                  <Star className="w-3 h-3 fill-black" />
                  MOST POPULAR
                </div>
              )}

              {!tier.isPopular && isCurrentPlan(tier.name) && (
                <div className={cn(
                  "absolute -top-4 left-1/2 transform -translate-x-1/2",
                  "px-4 py-1 border-[2px] border-black dark:border-white",
                  "bg-[#6EE7B7] text-black font-black text-xs uppercase tracking-wide",
                  "flex items-center gap-1"
                )}>
                  ✓ ACTIVE SUBSCRIPTION
                </div>
              )}

              <CardHeader className={cn(
                "border-b-[2px] border-black dark:border-white",
                tier.isPopular ? "bg-[#C4B5FD]" : "bg-[#FFD93D]"
              )}>
                <CardTitle className={cn(
                  "text-2xl font-black text-black uppercase"
                )}>
                  {tier.name}
                </CardTitle>
                <div className="mt-2">
                  <span className={cn(
                    "text-4xl font-black text-black"
                  )}>
                    {tier.price}
                  </span>
                  <span className={cn(
                    "text-sm font-bold text-black ml-1"
                  )}>
                    /month
                  </span>
                </div>
                <p className={cn(
                  "text-sm font-bold text-black mt-2"
                )}>
                  {tier.description}
                </p>
              </CardHeader>

              <CardContent className="pt-6">
                <ul className="space-y-3">
                  {tier.features.map((feature, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <Check className={cn(
                        "w-5 h-5 flex-shrink-0 mt-0.5 text-black dark:text-white"
                      )} />
                      <span className={cn(
                        "text-sm font-bold text-black dark:text-white"
                      )}>
                        {feature}
                      </span>
                    </li>
                  ))}
                </ul>
              </CardContent>

              <CardFooter>
                <Button
                  onClick={() => handleSelectPlan(tier.name)}
                  disabled={isLoading !== null || isCurrentPlan(tier.name) || loadingAccount}
                  className={cn(
                    "w-full py-3 font-black text-black transition-all transform",
                    "border-[2px] border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)]",
                    "active:translate-x-1 active:translate-y-1 active:shadow-none",
                    "uppercase",
                    (isLoading === tier.name || loadingAccount) && "opacity-50 cursor-not-allowed",
                    isCurrentPlan(tier.name) && "opacity-75 cursor-not-allowed",
                    tier.isPopular
                      ? "bg-[#C4B5FD] hover:bg-[#C4B5FD]"
                      : "bg-[#FFD93D] hover:bg-[#FFD93D]"
                  )}
                >
                  {loadingAccount 
                    ? 'Loading...' 
                    : isLoading === tier.name 
                      ? 'Processing...' 
                      : isCurrentPlan(tier.name)
                        ? '✓ Current Plan'
                        : tier.buttonText}
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>

        {error && (
          <div className={cn(
            "mt-8 text-center p-4 border-[3px] border-red-500",
            "bg-red-50 dark:bg-red-900/20 shadow-[2px_2px_0_0_rgba(239,68,68,1)]"
          )}>
            <p className={cn(
              "text-sm font-bold text-red-600 dark:text-red-400"
            )}>
              {error}
            </p>
          </div>
        )}

        <div className={cn(
          "mt-8 md:mt-12 text-center p-6 border-[3px] border-black dark:border-white",
          "bg-[#FFFDF5] dark:bg-[#000000] shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]"
        )}>
          <p className={cn(
            "text-sm font-bold text-black dark:text-white"
          )}>
            All plans include a 7-day free trial. Cancel anytime.
          </p>
        </div>
      </div>
    </div>
    </>
  );
};

export default PricingPage;

