"use client";

import { useState } from "react";
import { useAuthStore } from "@/store/auth";
import { authApi } from "@/lib/api";
import { toast } from "sonner";
import { useMutation } from "@tanstack/react-query";
import { Loader2, User, Mail, Lock } from "lucide-react";

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const [name, setName] = useState(user?.name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [newPassword, setNewPassword] = useState("");

  const updateMutation = useMutation({
    mutationFn: () => authApi.updateMe({ name, email, password: newPassword || undefined }),
    onSuccess: (res) => {
      setUser(res.data);
      toast.success("Settings updated");
    },
    onError: () => toast.error("Failed to update settings"),
  });

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Manage your account</p>
      </div>

      <div className="card p-6 space-y-6">
        <div className="space-y-4">
          <h3 className="text-lg font-medium">Profile</h3>
          <div>
            <label className="block text-sm font-medium mb-1">Full Name</label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="input pl-10" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="input pl-10" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Role</label>
            <input type="text" value={user?.role || ""} disabled className="input bg-gray-50 dark:bg-gray-700 capitalize" />
          </div>
        </div>

        <div className="pt-6 border-t border-gray-200 dark:border-gray-700 space-y-4">
          <h3 className="text-lg font-medium">Change Password</h3>
          <div>
            <label className="block text-sm font-medium mb-1">New Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
                className="input pl-10" placeholder="Leave blank to keep current" minLength={8} />
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <button onClick={() => updateMutation.mutate()} disabled={updateMutation.isPending}
            className="btn-primary flex items-center gap-2">
            {updateMutation.isPending ? <><Loader2 className="h-4 w-4 animate-spin" /> Saving...</> : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
