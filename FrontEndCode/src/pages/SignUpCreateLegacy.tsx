import React, { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import Logo from "@/components/Logo";
import CreateLegacyFormFields from "@/components/signup/CreateLegacyFormFields";

const SignUpCreateLegacy = () => {
  const [searchParams] = useSearchParams();
  const [inviteToken, setInviteToken] = useState<string | null>(null);
  const [isInvited, setIsInvited] = useState(false);

  useEffect(() => {
    const inviteParam = searchParams.get('invite');
    if (inviteParam) {
      setInviteToken(inviteParam);
      setIsInvited(true);
    }
  }, [searchParams]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <div className="flex justify-center mb-4">
            <Link to="/"><Logo /></Link>
          </div>
          <CardTitle className="text-2xl font-bold text-center">
            {isInvited ? "Accept Your Legacy Invitation" : "Preserve Your Legacy"}
          </CardTitle>
          <CardDescription className="text-center">
            {isInvited
              ? "You've been invited to create your legacy on SoulReel. Create an account to get started."
              : "Create an account to start recording your memories and experiences"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <CreateLegacyFormFields
            inviteToken={inviteToken}
            showInviteBanner={isInvited}
          />
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

export default SignUpCreateLegacy;
