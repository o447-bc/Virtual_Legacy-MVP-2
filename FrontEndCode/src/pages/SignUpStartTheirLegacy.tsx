import React from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import Logo from "@/components/Logo";
import StartTheirLegacyFormFields from "@/components/signup/StartTheirLegacyFormFields";

const SignUpStartTheirLegacy = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <div className="flex justify-center mb-4">
            <Link to="/"><Logo /></Link>
          </div>
          <CardTitle className="text-2xl font-bold text-center">Start Legacy for Someone Else</CardTitle>
          <CardDescription className="text-center">
            Create an account to help preserve someone else's memories and experiences
          </CardDescription>
        </CardHeader>
        <CardContent>
          <StartTheirLegacyFormFields />
        </CardContent>
        <CardFooter>
          <p className="text-center text-sm text-gray-600 mt-2 w-full">
            Already have an account?{" "}
            <Link to="/login" className="text-legacy-purple hover:underline font-medium">Sign in</Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  );
};

export default SignUpStartTheirLegacy;
