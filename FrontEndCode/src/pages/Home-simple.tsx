import React from "react";
import { useAuth } from "@/contexts/AuthContext-simple";

const Home = () => {
  const { user } = useAuth();

  return (
    <div style={{ padding: '20px' }}>
      <h1>Virtual Legacy</h1>
      <p>Home page is working!</p>
      <p>User: {user ? 'Logged in' : 'Not logged in'}</p>
    </div>
  );
};

export default Home;