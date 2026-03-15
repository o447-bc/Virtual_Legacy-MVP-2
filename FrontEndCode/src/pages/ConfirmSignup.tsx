import React, { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts/AuthContext";
import Logo from "@/components/Logo";

const ConfirmSignup = () => {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [errors, setErrors] = useState({ email: "", code: "" });
  const location = useLocation();
  
  const { confirmSignup, resendConfirmationCode, isLoading } = useAuth();

  useEffect(() => {
    // Extract email from URL query params if available
    const params = new URLSearchParams(location.search);
    const emailParam = params.get("email");
    if (emailParam) {
      setEmail(emailParam);
    }
  }, [location]);

  const validateForm = () => {
    let isValid = true;
    const newErrors = { email: "", code: "" };
    
    if (!email) {
      newErrors.email = "Email is required";
      isValid = false;
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      newErrors.email = "Email is invalid";
      isValid = false;
    }
    
    if (!code) {
      newErrors.code = "Verification code is required";
      isValid = false;
    }
    
    setErrors(newErrors);
    return isValid;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (validateForm()) {
      await confirmSignup(email, code);
    }
  };

  const handleResendCode = async () => {
    if (!email) {
      setErrors({ ...errors, email: "Email is required to resend code" });
      return;
    }
    
    if (!/\S+@\S+\.\S+/.test(email)) {
      setErrors({ ...errors, email: "Email is invalid" });
      return;
    }
    
    await resendConfirmationCode(email);
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
          <CardTitle className="text-2xl font-bold text-center">Verify your email</CardTitle>
          <CardDescription className="text-center">
            Enter the verification code sent to your email
          </CardDescription>
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
                disabled={!!location.search.includes("email=")}
              />
              {errors.email && <p className="text-sm text-red-500">{errors.email}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="code">Verification Code</Label>
              <Input 
                id="code" 
                type="text" 
                placeholder="Enter verification code" 
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
              {errors.code && <p className="text-sm text-red-500">{errors.code}</p>}
            </div>
            <Button 
              type="submit" 
              className="w-full bg-legacy-purple hover:bg-legacy-navy" 
              disabled={isLoading}
            >
              {isLoading ? "Verifying..." : "Verify Email"}
            </Button>
          </form>
          <div className="mt-4 text-center">
            <Button 
              variant="link" 
              onClick={handleResendCode}
              disabled={isLoading}
              className="text-legacy-purple hover:text-legacy-navy"
            >
              Resend verification code
            </Button>
          </div>
        </CardContent>
        <CardFooter>
          <p className="text-center text-sm text-gray-600 mt-2 w-full">
            Already verified?{" "}
            <Link to="/login" className="text-legacy-purple hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  );
};

export default ConfirmSignup;