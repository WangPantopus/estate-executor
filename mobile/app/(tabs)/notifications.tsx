/**
 * Notifications tab — wraps the NotificationsScreen.
 * Handles deep link navigation from notification taps.
 */

import React, { useEffect } from "react";
import { SafeAreaView, StyleSheet } from "react-native";
import { useRouter } from "expo-router";
import { NotificationsScreen } from "@/screens/tabs/NotificationsScreen";
import { useNotifications } from "@/hooks/useNotifications";
import { colors } from "@/lib/theme";

export default function NotificationsTab() {
  const router = useRouter();
  const { pendingDeepLink, consumeDeepLink } = useNotifications();

  // Handle deep links from notification taps
  useEffect(() => {
    if (!pendingDeepLink) return;

    // Navigate based on deep link target
    if (pendingDeepLink.screen === "matterDetail" && pendingDeepLink.matterId) {
      // Switch to Matters tab and navigate to detail
      router.navigate("/(tabs)");
    } else if (pendingDeepLink.screen === "taskDetail" && pendingDeepLink.matterId && pendingDeepLink.taskId) {
      router.navigate("/(tabs)");
    }

    consumeDeepLink();
  }, [pendingDeepLink, consumeDeepLink, router]);

  return (
    <SafeAreaView style={styles.container}>
      <NotificationsScreen
        onNavigateToMatter={() => {
          // Navigate to matters tab — the matter detail navigation
          // is handled by the stack in the matters tab
          router.navigate("/(tabs)");
        }}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
});
