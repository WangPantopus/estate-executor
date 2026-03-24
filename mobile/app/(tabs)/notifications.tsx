/**
 * Notifications tab — wraps the NotificationsScreen.
 */

import React from "react";
import { SafeAreaView, StyleSheet } from "react-native";
import { NotificationsScreen } from "@/screens/tabs/NotificationsScreen";
import { colors } from "@/lib/theme";

export default function NotificationsTab() {
  return (
    <SafeAreaView style={styles.container}>
      <NotificationsScreen />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
});
