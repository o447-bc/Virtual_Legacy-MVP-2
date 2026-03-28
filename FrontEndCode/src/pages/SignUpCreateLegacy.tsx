import React, { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts/AuthContext";
import Logo from "@/components/Logo";

const SignUpCreateLegacy = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [errors, setErrors] = useState({ email: "", password: "", confirmPassword: "", firstName: "", lastName: "" });
  const [inviteToken, setInviteToken] = useState<string | null>(null);
  const [isInvited, setIsInvited] = useState(false);
  
  const { signupWithPersona, isLoading } = useAuth();
  const [searchParams] = useSearchParams();
  
  // Check for invite token in URL parameters on component mount
  useEffect(() => {
    const inviteParam = searchParams.get('invite');
    if (inviteParam) {
      setInviteToken(inviteParam);
      setIsInvited(true);
    }
  }, [searchParams]);

  const validateForm = () => {
    let isValid = true;
    const newErrors = { email: "", password: "", confirmPassword: "", firstName: "", lastName: "" };
    
    if (!email) {
      newErrors.email = "Email is required";
      isValid = false;
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      newErrors.email = "Email is invalid";
      isValid = false;
    }
    
    if (!firstName) {
      newErrors.firstName = "First name is required";
      isValid = false;
    } else if (!/^[a-zA-Z\s\-']{2,50}$/.test(firstName)) {
      newErrors.firstName = "First name must be 2-50 characters (letters only)";
      isValid = false;
    }
    
    if (!lastName) {
      newErrors.lastName = "Last name is required";
      isValid = false;
    } else if (!/^[a-zA-Z\s\-']{2,50}$/.test(lastName)) {
      newErrors.lastName = "Last name must be 2-50 characters (letters only)";
      isValid = false;
    }
    
    if (!password) {
      newErrors.password = "Password is required";
      isValid = false;
    } else if (password.length < 8) {
      newErrors.password = "Password must be at least 8 characters long";
      isValid = false;
    } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(password)) {
      newErrors.password = "Password must contain uppercase, lowercase, and number";
      isValid = false;
    }
    
    if (!confirmPassword) {
      newErrors.confirmPassword = "Please confirm your password";
      isValid = false;
    } else if (password !== confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match";
      isValid = false;
    }
    
    setErrors(newErrors);
    return isValid;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (validateForm()) {
      const normalizedEmail = email.toLowerCase();
      // If user came from an invite, include the invite token in clientMetadata
      if (isInvited && inviteToken) {
        // Pass invite token as additional clientMetadata for postConfirmation trigger
        await signupWithPersona(normalizedEmail, password, "create_legacy_invited", "legacy_maker", firstName, lastName, inviteToken);
      } else {
        // Normal signup without invite
        await signupWithPersona(normalizedEmail, password, "create_legacy", "legacy_maker", firstName, lastName);
      }
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <div className="flex justify-center mb-4">
            <Link to="/">
              <Logo />
            </Link>
          </div>
          <CardTitle className="text-2xl font-bold text-center">
            {isInvited ? "Accept Your Legacy Invitation" : "Preserve Your Legacy"}
          </CardTitle>
          <CardDescription className="text-center">
            {isInvited 
              ? "You've been invited to create your legacy on SoulReel. Create an account to get started."
              : "Create an account to start recording your memories and experiences"
            }
          </CardDescription>
          {isInvited && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mt-4">
              <p className="text-sm text-blue-700">
                ✉️ You're signing up through an invitation. Your account will be automatically linked to your benefactor.
              </p>
            </div>
          )}
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input 
                id="email" 
                type="email" 
                placeholder="your@email.com" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              {errors.email && <p className="text-sm text-red-500">{errors.email}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="firstName">First Name</Label>
              <Input 
                id="firstName" 
                type="text" 
                placeholder="John" 
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
              />
              {errors.firstName && <p className="text-sm text-red-500">{errors.firstName}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="lastName">Last Name</Label>
              <Input 
                id="lastName" 
                type="text" 
                placeholder="Smith" 
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
              />
              {errors.lastName && <p className="text-sm text-red-500">{errors.lastName}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input 
                id="password" 
                type="password" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              {errors.password && <p className="text-sm text-red-500">{errors.password}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <Input 
                id="confirmPassword" 
                type="password" 
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
              {errors.confirmPassword && <p className="text-sm text-red-500">{errors.confirmPassword}</p>}
            </div>
            <Button 
              type="submit" 
              className="w-full bg-legacy-purple hover:bg-legacy-navy" 
              disabled={isLoading}
            >
              {isLoading ? "Creating account..." : "Create Your Legacy"}
            </Button>
          </form>
        </CardContent>
        <CardFooter>
          <p className="text-center text-sm text-gray-600 mt-2 w-full">
            Already have an account?{" "}
            <Link to="/login" className="text-legacy-purple hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  );
};

export default SignUpCreateLegacy;