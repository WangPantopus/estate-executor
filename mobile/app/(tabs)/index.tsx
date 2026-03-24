/**
 * Matters tab — wraps the MattersScreen.
 */

import React from "react";
import { SafeAreaView, StyleSheet } from "react-native";
import { MattersScreen } from "@/screens/tabs/MattersScreen";
import { colors } from "@/lib/theme";

export default function MattersTab() {
  return (
    <SafeAreaView style={styles.container}>
      <MattersScreen />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
});
