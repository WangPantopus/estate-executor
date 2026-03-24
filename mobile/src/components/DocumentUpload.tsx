/**
 * Document upload component — camera capture + photo library picker.
 */

import React, { useState } from "react";
import { Alert, StyleSheet, Text, View, ActivityIndicator, Image } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { Ionicons } from "@expo/vector-icons";
import { Button, Card } from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { colors, spacing, fontSize, fontWeight, borderRadius } from "@/lib/theme";

interface DocumentUploadProps {
  firmId: string;
  matterId: string;
  taskId?: string;
  onUploaded?: (docId: string) => void;
}

export function DocumentUpload({
  firmId,
  matterId,
  taskId,
  onUploaded,
}: DocumentUploadProps) {
  const { api } = useAuth();
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  const pickImage = async (useCamera: boolean) => {
    // Request permissions
    if (useCamera) {
      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      if (status !== "granted") {
        Alert.alert("Permission needed", "Camera access is required to capture documents.");
        return;
      }
    } else {
      const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (status !== "granted") {
        Alert.alert("Permission needed", "Photo library access is required to select documents.");
        return;
      }
    }

    const result = useCamera
      ? await ImagePicker.launchCameraAsync({
          mediaTypes: ["images"],
          quality: 0.8,
          allowsEditing: true,
        })
      : await ImagePicker.launchImageLibraryAsync({
          mediaTypes: ["images"],
          quality: 0.8,
          allowsEditing: true,
        });

    if (result.canceled || !result.assets[0]) return;

    const asset = result.assets[0];
    setPreview(asset.uri);
    await uploadDocument(asset);
  };

  const uploadDocument = async (asset: ImagePicker.ImagePickerAsset) => {
    setUploading(true);
    try {
      const filename = asset.fileName ?? `document_${Date.now()}.jpg`;
      const mimeType = asset.mimeType ?? "image/jpeg";

      // 1. Get pre-signed upload URL
      const { upload_url, storage_key } = await api.getUploadUrl(
        firmId,
        matterId,
        { filename, mime_type: mimeType },
      );

      // 2. Upload file to pre-signed URL
      const fileResponse = await fetch(asset.uri);
      const blob = await fileResponse.blob();

      await fetch(upload_url, {
        method: "PUT",
        headers: { "Content-Type": mimeType },
        body: blob,
      });

      // 3. Register document
      const doc = await api.registerDocument(firmId, matterId, {
        filename,
        storage_key,
        mime_type: mimeType,
        size_bytes: asset.fileSize ?? blob.size,
        task_id: taskId,
      });

      // 4. Link to task if provided
      if (taskId && doc.id) {
        await api.linkTaskDocument(firmId, matterId, taskId, doc.id);
      }

      onUploaded?.(doc.id);
      Alert.alert("Success", "Document uploaded successfully.");
    } catch (error) {
      Alert.alert("Upload failed", "Could not upload the document. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card style={styles.container}>
      <Text style={styles.title}>Upload Document</Text>
      <Text style={styles.subtitle}>
        Capture with camera or select from your photo library
      </Text>

      {preview && (
        <View style={styles.previewContainer}>
          <Image source={{ uri: preview }} style={styles.preview} />
          {uploading && (
            <View style={styles.uploadingOverlay}>
              <ActivityIndicator size="large" color={colors.white} />
              <Text style={styles.uploadingText}>Uploading...</Text>
            </View>
          )}
        </View>
      )}

      <View style={styles.buttons}>
        <Button
          title="Camera"
          variant="primary"
          size="sm"
          icon={<Ionicons name="camera-outline" size={18} color={colors.white} />}
          onPress={() => pickImage(true)}
          disabled={uploading}
        />
        <Button
          title="Photo Library"
          variant="outline"
          size="sm"
          icon={<Ionicons name="images-outline" size={18} color={colors.foreground} />}
          onPress={() => pickImage(false)}
          disabled={uploading}
        />
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.md,
  },
  title: {
    fontSize: fontSize.base,
    fontWeight: fontWeight.semibold,
    color: colors.foreground,
  },
  subtitle: {
    fontSize: fontSize.sm,
    color: colors.foregroundMuted,
  },
  previewContainer: {
    borderRadius: borderRadius.md,
    overflow: "hidden",
    position: "relative",
  },
  preview: {
    width: "100%",
    height: 200,
    borderRadius: borderRadius.md,
  },
  uploadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0,0,0,0.5)",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
  },
  uploadingText: {
    color: colors.white,
    fontSize: fontSize.sm,
    fontWeight: fontWeight.medium,
  },
  buttons: {
    flexDirection: "row",
    gap: spacing.md,
  },
});
