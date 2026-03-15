import React, { createContext, useContext, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "@/components/ui/sonner";
import { signIn, signUp, signOut, getCurrentUser, confirmSignUp, resendSignUpCode, fetchUserAttributes } from 'aws-amplify/auth';

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, firstName: string, lastName: string) => Promise<void>;
  signupWithPersona: (email: string, password: string, personaChoice: string, personaType: string, firstName: string, lastName: string, inviteToken?: string) => Promise<void>;
  confirmSignup: (email: string, code: string) => Promise<void>;
  resendConfirmationCode: (email: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  isLoading: boolean;
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
        const userAttributes = await fetchUserAttributes({ forceRefresh: true });
        console.log('Fetched user attributes (with refresh):', userAttributes);
        
        if (userAttributes.profile) {
          console.log('Profile data found:', userAttributes.profile);
          const profileJson = JSON.parse(userAttributes.profile);
          console.log('Parsed profile JSON:', profileJson);
          personaType = profileJson.persona_type || 'legacy_maker';
          console.log('Final persona type:', personaType);
        } else {
          console.log('No profile attribute found in fetched attributes');
          console.log('Available attributes:', Object.keys(userAttributes));
        }
        
        // Extract first and last names
        if (userAttributes.given_name) {
          firstName = userAttributes.given_name;
        }
        if (userAttributes.family_name) {
          lastName = userAttributes.family_name;
        }
      } catch (parseError) {
        console.log('Error parsing persona type:', parseError);
        console.log('Defaulting to legacy_maker');
      }
      
      setUser({
        email: currentUser.signInDetails?.loginId || '',
        id: currentUser.userId,
        personaType: personaType,
        firstName,
        lastName
      });
    } catch (error) {
      setUser(null);
    } finally {
      setIsLoading(false);
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
                }).catch(() => {}); // Silent fail
              }
            } catch (error) {
              console.warn('Progress initialization failed:', error);
            }
          }
        }
        
        toast.success("Logged in successfully");
        navigate("/dashboard");
      }
    } catch (error: any) {
      // Handle "already signed in" scenario
      if (error.name === 'UserAlreadyAuthenticatedException' || 
          error.message?.toLowerCase().includes('already') ||
          error.message?.toLowerCase().includes('signed in')) {
        
        console.log("User already authenticated, refreshing state");
        await checkAuthState();
        toast.info("You are already signed in");
        navigate("/dashboard");
        return;
      }
      
      // Handle all other errors
      toast.error(error.message || "Login failed. Please try again.");
      console.error("Login error:", error);
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
      console.error("Signup error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const signupWithPersona = async (email: string, password: string, personaChoice: string, personaType: string, firstName: string, lastName: string, inviteToken?: string) => {
    setIsLoading(true);
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
            // postConfirmation Lambda runs asynchronously and may not have finished writing
            // the profile attribute to Cognito yet (race condition). We call checkAuthState
            // to get the real user.id, then forcibly set personaType to 'legacy_benefactor'
            // because we know from the invite context that this user is a benefactor.
            await checkAuthState();
            setUser(prev => prev ? { ...prev, personaType: 'legacy_benefactor' } : prev);
            toast.success("Account created! Welcome to SoulReel.");
            navigate('/benefactor-dashboard');
            return;
          }
        } catch (signInError: any) {
          console.error('Auto sign-in after invite signup failed:', signInError);
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
      console.error("Signup error:", error);
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
        console.log('No existing session to sign out');
      }
      
      await confirmSignUp({ username: email.toLowerCase(), confirmationCode: code });
      toast.success("Email verified! You can now sign in.");
      navigate("/login");
    } catch (error: any) {
      toast.error(error.message || "Verification failed. Please try again.");
      console.error("Confirmation error:", error);
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
      console.error("Resend code error:", error);
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
      
      setUser(null);
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
    <AuthContext.Provider value={{ user, login, signup, signupWithPersona, confirmSignup, resendConfirmationCode, logout, refreshUser: checkAuthState, isLoading }}>
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
