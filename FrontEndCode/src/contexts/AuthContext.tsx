import React, { createContext, useContext, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "@/components/ui/sonner";
import { signIn, signUp, signOut, getCurrentUser, confirmSignUp, resendSignUpCode, fetchUserAttributes, resetPassword as amplifyResetPassword, confirmResetPassword } from 'aws-amplify/auth';
import { getSurveyStatus } from '@/services/surveyService';

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, firstName: string, lastName: string) => Promise<void>;
  signupWithPersona: (email: string, password: string, personaChoice: string, personaType: string, firstName: string, lastName: string, inviteToken?: string) => Promise<void>;
  confirmSignup: (email: string, code: string) => Promise<void>;
  resendConfirmationCode: (email: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  forgotPassword: (email: string) => Promise<void>;
  resetPassword: (email: string, code: string, newPassword: string) => Promise<void>;
  isLoading: boolean;
  hasCompletedSurvey: boolean | null;
  refreshSurveyStatus: () => Promise<void>;
}

interface User {
  email: string;
  id: string;
  personaType: string;
  firstName?: string;
  lastName?: string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [hasCompletedSurvey, setHasCompletedSurvey] = useState<boolean | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    checkAuthState();
  }, []);

  const checkAuthState = async () => {
    try {
      const currentUser = await getCurrentUser();
      
      // Parse persona type and names from user attributes
      let personaType = 'legacy_maker'; // Default fallback
      let firstName: string | undefined;
      let lastName: string | undefined;
      try {
        // Force fresh fetch of user attributes
        let userAttributes = await fetchUserAttributes({ forceRefresh: true });
        
        // If profile is missing, postConfirmation Lambda may still be running.
        // Wait briefly and retry once to cover the race condition.
        if (!userAttributes.profile) {
          await new Promise(r => setTimeout(r, 2000));
          userAttributes = await fetchUserAttributes({ forceRefresh: true });
        }
        
        if (userAttributes.profile) {
          const profileJson = JSON.parse(userAttributes.profile);
          personaType = profileJson.persona_type || 'legacy_maker';
        }
        
        // Extract first and last names
        if (userAttributes.given_name) {
          firstName = userAttributes.given_name;
        }
        if (userAttributes.family_name) {
          lastName = userAttributes.family_name;
        }
      } catch (parseError) {
        // Defaulting to legacy_maker
      }
      
      setUser({
        email: currentUser.signInDetails?.loginId || '',
        id: currentUser.userId,
        personaType: personaType,
        firstName,
        lastName
      });
      
      // Fetch survey status for legacy makers
      if (personaType === 'legacy_maker') {
        try {
          const surveyStatus = await getSurveyStatus();
          setHasCompletedSurvey(surveyStatus.hasCompletedSurvey);
        } catch (surveyErr) {
          console.error('Failed to fetch survey status:', surveyErr);
          setHasCompletedSurvey(null);
        }
      } else {
        // Non-legacy-makers don't need the survey
        setHasCompletedSurvey(true);
      }
    } catch (error) {
      setUser(null);
      setHasCompletedSurvey(null);
    } finally {
      setIsLoading(false);
    }
  };

  const refreshSurveyStatus = async () => {
    try {
      const surveyStatus = await getSurveyStatus();
      setHasCompletedSurvey(surveyStatus.hasCompletedSurvey);
    } catch (err) {
      console.error('Failed to refresh survey status:', err);
    }
  };

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const { isSignedIn } = await signIn({ username: email.toLowerCase(), password });
      if (isSignedIn) {
        await checkAuthState();
        
        // Initialize progress for legacy makers
        const currentUser = await getCurrentUser();
        const userAttributes = await fetchUserAttributes();
        if (userAttributes.profile) {
          const profileJson = JSON.parse(userAttributes.profile);
          if (profileJson.persona_type === 'legacy_maker') {
            try {
              const session = await import('aws-amplify/auth').then(auth => auth.fetchAuthSession());
              const token = session.tokens?.idToken?.toString();
              if (token) {
                const { buildApiUrl } = await import('../config/api');
                fetch(buildApiUrl('/functions/questionDbFunctions/initialize-progress'), {
                  method: 'POST',
                  headers: { Authorization: `Bearer ${token}` }
                }).catch((err) => {
                  console.warn('Progress initialization request failed:', err);
                });
              }
            } catch (error) {
              console.warn('Progress initialization failed:', error);
            }
          }
        }
        
        toast.success("Logged in successfully");
        const dest = userAttributes.profile && JSON.parse(userAttributes.profile).persona_type === 'legacy_benefactor'
          ? '/benefactor-dashboard'
          : '/dashboard';
        navigate(dest);
      }
    } catch (error: any) {
      // Handle "already signed in" scenario
      if (error.name === 'UserAlreadyAuthenticatedException' || 
          error.message?.toLowerCase().includes('already') ||
          error.message?.toLowerCase().includes('signed in')) {
        
        await checkAuthState();
        toast.info("You are already signed in");
        // checkAuthState has updated user state; ProtectedRoute + Login.tsx useEffect will handle routing
        return;
      }
      
      // Handle all other errors
      toast.error(error.message || "Login failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (email: string, password: string, firstName: string, lastName: string) => {
    setIsLoading(true);
    try {
      const normalizedEmail = email.toLowerCase();
      await signUp({
        username: normalizedEmail,
        password,
        options: {
          userAttributes: {
            email: normalizedEmail
          },
          clientMetadata: {
            first_name: firstName,
            last_name: lastName
          }
        }
      });
      toast.success("Account created! Please check your email for verification.");
      navigate(`/confirm-signup?email=${encodeURIComponent(email)}`);
    } catch (error: any) {
      toast.error(error.message || "Signup failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const signupWithPersona = async (email: string, password: string, personaChoice: string, personaType: string, firstName: string, lastName: string, inviteToken?: string) => {
    try {
      const normalizedEmail = email.toLowerCase();
      const clientMetadata: Record<string, string> = {
        persona_choice: personaChoice,
        persona_type: personaType,
        first_name: firstName,
        last_name: lastName
      };
      if (inviteToken) {
        clientMetadata.invite_token = inviteToken;
      }
      
      const signUpResult = await signUp({
        username: normalizedEmail,
        password,
        options: {
          userAttributes: { email: normalizedEmail },
          clientMetadata
        }
      });

      // Invited benefactors: preSignup Lambda sets autoConfirmUser=true so the account
      // is confirmed immediately. We sign in directly — no confirmation code needed.
      if (inviteToken && signUpResult.isSignUpComplete) {
        // Sign out any existing session (e.g. the legacy maker who was logged in)
        // before signing in as the new benefactor.
        try { await signOut(); } catch (_) { /* nothing to sign out */ }

        try {
          const signInResult = await signIn({ username: normalizedEmail, password });

          if (signInResult.isSignedIn) {
            // Poll for the postConfirmation Lambda to finish writing the persona attribute.
            // The Lambda runs async after Cognito confirms the user — without polling we'd
            // race and potentially read a missing/wrong persona_type.
            const waitForPersona = async (expected: string, maxAttempts = 5): Promise<boolean> => {
              for (let i = 0; i < maxAttempts; i++) {
                try {
                  const attrs = await fetchUserAttributes({ forceRefresh: true });
                  if (attrs.profile) {
                    const profile = JSON.parse(attrs.profile);
                    if (profile.persona_type === expected) return true;
                  }
                } catch { /* retry */ }
                await new Promise(r => setTimeout(r, 1000 * (i + 1)));
              }
              return false;
            };

            const personaReady = await waitForPersona('legacy_benefactor');
            if (!personaReady) {
              toast.warning("Account setup is still processing. If something looks off, try refreshing the page.");
            }
            await checkAuthState();
            toast.success("Account created! Welcome to SoulReel.");
            navigate('/benefactor-dashboard');
            return;
          }
        } catch (signInError: any) {
          // Auto sign-in after invite signup failed — fall through to login
        }

        // Auto sign-in failed for any reason — account was created, send to login
        toast.success("Account created! Please sign in to continue.");
        navigate('/login');
        return;
      }

      // Non-invite signup: user needs to confirm their email
      toast.success("Account created! Please check your email for verification.");
      navigate(`/confirm-signup?email=${encodeURIComponent(email)}`);
    } catch (error: any) {
      toast.error(error.message || "Signup failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const confirmSignup = async (email: string, code: string) => {
    setIsLoading(true);
    try {
      // Sign out any existing user first to prevent wrong user login
      try {
        await signOut();
        setUser(null);
      } catch (signOutError) {
        // Ignore if no user is signed in
      }
      
      await confirmSignUp({ username: email.toLowerCase(), confirmationCode: code });
      toast.success("Email verified! You can now sign in.");
      navigate("/login");
    } catch (error: any) {
      toast.error(error.message || "Verification failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const resendConfirmationCode = async (email: string) => {
    setIsLoading(true);
    try {
      await resendSignUpCode({ username: email.toLowerCase() });
      toast.success("Verification code sent! Check your email.");
    } catch (error: any) {
      toast.error(error.message || "Failed to resend code. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const forgotPassword = async (email: string) => {
    setIsLoading(true);
    try {
      await amplifyResetPassword({ username: email.toLowerCase() });
      toast.success("Reset code sent! Check your email.");
      navigate(`/reset-password?email=${encodeURIComponent(email)}`);
    } catch (error: any) {
      toast.error(error.message || "Failed to send reset code. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const resetPassword = async (email: string, code: string, newPassword: string) => {
    setIsLoading(true);
    try {
      await confirmResetPassword({ username: email.toLowerCase(), confirmationCode: code, newPassword });
      toast.success("Password reset! You can now sign in.");
      navigate("/login");
    } catch (error: any) {
      toast.error(error.message || "Failed to reset password. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await signOut();
      
      // Clear cached user data
      if (user?.id) {
        // Clear statistics cache
        const statisticsCacheKey = `user_statistics_${user.id}`;
        localStorage.removeItem(statisticsCacheKey);
      }
      // Clear survey dismiss flag so it shows again on next login
      try { sessionStorage.removeItem('surveyDismissed'); } catch { /* ignore */ }
      
      setUser(null);
      setHasCompletedSurvey(null);
      toast.info("Logged out successfully");
      navigate("/");
    } catch (error: any) {
      // Log error for debugging (Requirements 13.5, 13.6)
      console.error("Logout error:", error);
      
      // Display user-friendly error message without sensitive information (Requirements 13.4, 13.6, 13.7)
      const errorMessage = "Failed to log out. Please try again.";
      toast.error(errorMessage, {
        action: {
          label: "Retry",
          onClick: () => logout(),
        },
      });
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, signup, signupWithPersona, confirmSignup, resendConfirmationCode, logout, refreshUser: checkAuthState, forgotPassword, resetPassword, isLoading, hasCompletedSurvey, refreshSurveyStatus }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
