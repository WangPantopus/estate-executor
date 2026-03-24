/**
 * Profile tab — wraps the ProfileScreen.
 */

import React from "react";
import { SafeAreaView, StyleSheet } from "react-native";
import { ProfileScreen } from "@/screens/tabs/ProfileScreen";
import { colors } from "@/lib/theme";

export default function ProfileTab() {
  return (
    <SafeAreaView style={styles.container}>
      <ProfileScreen />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
});
