/**
 * Tab navigator — Matters, Notifications, Profile.
 * Shows unread badge count on notifications tab.
 */

import React from "react";
import { Tabs } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useNotifications } from "@/hooks/useNotifications";
import { colors } from "@/lib/theme";

export default function TabLayout() {
  const { unreadCount } = useNotifications();

  return (
    <Tabs
      screenOptions={{
        headerShown: true,
        headerStyle: {
          backgroundColor: colors.surface,
          shadowColor: "transparent",
          elevation: 0,
        },
        headerTintColor: colors.foreground,
        headerTitleStyle: {
          fontWeight: "600",
          fontSize: 17,
        },
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          borderTopWidth: 0.5,
          height: 88,
          paddingBottom: 32,
          paddingTop: 8,
        },
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.foregroundLight,
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: "500",
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Matters",
          headerShown: false,
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="briefcase-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="notifications"
        options={{
          title: "Notifications",
          headerShown: false,
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="notifications-outline" size={size} color={color} />
          ),
          tabBarBadge: unreadCount > 0 ? unreadCount : undefined,
          tabBarBadgeStyle: {
            backgroundColor: colors.danger,
            fontSize: 10,
            minWidth: 18,
            height: 18,
            lineHeight: 18,
          },
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Profile",
          headerShown: false,
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="person-outline" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
