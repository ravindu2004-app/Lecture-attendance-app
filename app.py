import React, { useState, useEffect } from "react";
import { GraduationCap, Lock, Mail, ArrowRight, UserCheck } from "lucide-react";

export default function AuthScreen() {
  const [isLogin, setIsLogin] = useState(true);
  const [greeting, setGreeting] = useState("");
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    fullName: "",
  });

  // Dynamic Greeting based on time of day
  useEffect(() => {
    const hour = new Date().getHours();
    if (hour < 12) setGreeting("Good Morning!");
    else if (hour < 18) setGreeting("Good Afternoon!");
    else setGreeting("Good Evening!");
  }, []);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (isLogin) {
      console.log("Logging in:", formData.email, formData.password);
    } else {
      console.log("Registering user:", formData);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center px-4 py-6 sm:px-6 lg:px-8">
      {/* Header Section - Compact & Professional */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center mb-6">
        <div className="inline-flex items-center justify-center p-3 bg-indigo-600/10 rounded-2xl border border-indigo-500/20 mb-3">
          <GraduationCap className="h-8 w-8 text-indigo-400" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-white">
          Attendance Tracker
        </h1>
        <p className="mt-1 text-sm text-indigo-300 font-medium">
          {greeting} Welcome back.
        </p>
      </div>

      {/* Main Form Container */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-slate-900/80 backdrop-blur-xl py-6 px-5 shadow-2xl rounded-2xl border border-slate-800">
          
          {/* Login / Register Toggle Tabs */}
          <div className="flex bg-slate-950/60 p-1 rounded-xl mb-6 border border-slate-800">
            <button
              onClick={() => setIsLogin(true)}
              className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all duration-200 ${
                isLogin
                  ? "bg-indigo-600 text-white shadow-lg"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => setIsLogin(false)}
              className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all duration-200 ${
                !isLogin
                  ? "bg-indigo-600 text-white shadow-lg"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Register
            </button>
          </div>

          {/* Form */}
          <form className="space-y-4" onSubmit={handleSubmit}>
            {!isLogin && (
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  Full Name
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <UserCheck className="h-4 w-4 text-slate-500" />
                  </div>
                  <input
                    name="fullName"
                    type="text"
                    required
                    value={formData.fullName}
                    onChange={handleChange}
                    placeholder="John Doe"
                    className="block w-full pl-10 pr-3 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-4 w-4 text-slate-500" />
                </div>
                <input
                  name="email"
                  type="email"
                  required
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="student@university.ac.lk"
                  className="block w-full pl-10 pr-3 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-4 w-4 text-slate-500" />
                </div>
                <input
                  name="password"
                  type="password"
                  required
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="••••••••"
                  className="block w-full pl-10 pr-3 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                />
              </div>
            </div>

            {!isLogin && (
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  Confirm Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-4 w-4 text-slate-500" />
                  </div>
                  <input
                    name="confirmPassword"
                    type="password"
                    required
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    placeholder="••••••••"
                    className="block w-full pl-10 pr-3 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                  />
                </div>
              </div>
            )}

            {isLogin && (
              <div className="flex items-center justify-end">
                <button
                  type="button"
                  className="text-xs font-medium text-indigo-400 hover:text-indigo-300"
                >
                  Forgot password?
                </button>
              </div>
            )}

            <button
              type="submit"
              className="w-full flex justify-center items-center gap-2 py-3 px-4 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm rounded-xl shadow-lg shadow-indigo-600/30 transition-all duration-200 mt-2"
            >
              {isLogin ? "Sign In" : "Create Account"}
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
