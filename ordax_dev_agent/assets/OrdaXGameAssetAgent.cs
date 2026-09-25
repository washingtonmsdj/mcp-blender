#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace OrdaX.EditorTools
{
    [InitializeOnLoad]
    public static class OrdaXGameAssetAgent
    {
        [Serializable] private class Command
        {
            public string id, action, assetPath;
        }

        [Serializable] private class LodLevelEvidence
        {
            public int groupIndex, levelIndex, rendererCount, skinnedRendererCount;
            public float transitionHeight;
        }

        [Serializable] private class Reply
        {
            public string id, summary, protocol = "ordax-game-assets-v1";
            public bool ok;
            public string assetPath, animationType, avatarSetup;
            public bool sourceAvatarPresent, sourceAvatarValid, sourceAvatarHuman;
            public int avatarCount, avatarEvidenceCount, validAvatarCount, humanAvatarCount, humanoidMappedBoneCount;
            public int animationClipCount, rootCurveClipCount, motionCurveClipCount;
            public int humanMotionClipCount, genericRootTransformClipCount;
            public int animatorCount, animatorWithAvatarCount, humanAnimatorCount;
            public int meshRendererCount, skinnedMeshRendererCount, colliderCount;
            public int lodGroupCount, lodLevelCount, lodRendererCount, lodEmptyLevelCount;
            public LodLevelEvidence[] lodLevels;
        }

        private static string Root => Path.Combine(
            Directory.GetParent(Application.dataPath).FullName,
            "Library", "OrdaXAgent", "game-assets");
        private static double nextPoll;

        static OrdaXGameAssetAgent()
        {
            EditorApplication.update += Tick;
        }

        private static void Write(string path, object value)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            string temporary = path + ".tmp";
            File.WriteAllText(temporary, JsonUtility.ToJson(value, true));
            if (File.Exists(path)) File.Replace(temporary, path, null);
            else File.Move(temporary, path);
        }

        private static Reply State(string id, bool ok, string summary)
        {
            return new Reply { id = id, ok = ok, summary = summary };
        }

        private static void Tick()
        {
            if (EditorApplication.timeSinceStartup < nextPoll) return;
            nextPoll = EditorApplication.timeSinceStartup + 0.35;
            try
            {
                Write(Path.Combine(Root, "presence.json"), State("presence", true, "Game asset telemetry ready"));
                if (EditorApplication.isCompiling || EditorApplication.isUpdating) return;
                string inbox = Path.Combine(Root, "inbox");
                Directory.CreateDirectory(inbox);
                var files = Directory.GetFiles(inbox, "*.json");
                Array.Sort(files, StringComparer.Ordinal);
                if (files.Length > 0) Process(files[0]);
            }
            catch (IOException) { }
        }

        private static void Process(string file)
        {
            string id = Path.GetFileNameWithoutExtension(file);
            if (!Guid.TryParseExact(id, "N", out _))
            {
                File.Delete(file);
                return;
            }

            Reply reply;
            try
            {
                var command = JsonUtility.FromJson<Command>(File.ReadAllText(file));
                File.Delete(file);
                if (command == null || command.id != id)
                    throw new InvalidOperationException("Command ID mismatch");
                if (command.action != "asset_character_audit")
                    throw new InvalidOperationException("Unsupported game asset action: " + command.action);
                reply = State(id, true, "Unity game asset telemetry completed");
                CharacterAudit(command, reply);
            }
            catch (Exception error)
            {
                reply = State(id, false, error.GetType().Name + ": " + error.Message);
            }
            Write(Path.Combine(Root, "responses", id + ".json"), reply);
        }

        private static string ValidateAssetPath(string value)
        {
            string path = (value ?? "").Replace('\\', '/').Trim();
            if (!path.StartsWith("Assets/", StringComparison.Ordinal) ||
                path.Contains("/../") || path.EndsWith("/..", StringComparison.Ordinal))
                throw new InvalidOperationException("assetPath must stay inside Assets/");
            if (AssetDatabase.LoadMainAssetAtPath(path) == null)
                throw new InvalidOperationException("assetPath is not a loaded Unity asset");
            return path;
        }

        private static void CharacterAudit(Command command, Reply reply)
        {
            string assetPath = ValidateAssetPath(command.assetPath);
            var importer = AssetImporter.GetAtPath(assetPath) as ModelImporter;
            if (importer == null)
                throw new InvalidOperationException("assetPath is not backed by a ModelImporter");

            var allAssets = AssetDatabase.LoadAllAssetsAtPath(assetPath);
            var avatars = allAssets.OfType<Avatar>().ToArray();
            var clips = allAssets.OfType<AnimationClip>()
                .Where(clip => clip != null && !clip.name.StartsWith("__preview__", StringComparison.Ordinal))
                .ToArray();
            var modelRoot = AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);
            if (modelRoot == null)
                throw new InvalidOperationException("Unity did not expose the imported model root GameObject");

            var animators = modelRoot.GetComponentsInChildren<Animator>(true);
            var meshRenderers = modelRoot.GetComponentsInChildren<MeshRenderer>(true);
            var skinnedRenderers = modelRoot.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            var colliders = modelRoot.GetComponentsInChildren<Collider>(true);
            var lodGroups = modelRoot.GetComponentsInChildren<LODGroup>(true);
            var lodLevels = new List<LodLevelEvidence>();
            int lodRendererCount = 0;
            int lodEmptyLevelCount = 0;

            for (int groupIndex = 0; groupIndex < lodGroups.Length; groupIndex++)
            {
                var lods = lodGroups[groupIndex].GetLODs();
                for (int levelIndex = 0; levelIndex < lods.Length; levelIndex++)
                {
                    var renderers = lods[levelIndex].renderers ?? Array.Empty<Renderer>();
                    if (renderers.Length == 0) lodEmptyLevelCount++;
                    lodRendererCount += renderers.Length;
                    lodLevels.Add(new LodLevelEvidence
                    {
                        groupIndex = groupIndex,
                        levelIndex = levelIndex,
                        rendererCount = renderers.Length,
                        skinnedRendererCount = renderers.Count(renderer => renderer is SkinnedMeshRenderer),
                        transitionHeight = lods[levelIndex].screenRelativeTransitionHeight,
                    });
                }
            }

            Avatar sourceAvatar = importer.sourceAvatar;
            var avatarEvidence = new List<Avatar>();
            avatarEvidence.AddRange(avatars.Where(avatar => avatar != null));
            if (sourceAvatar != null) avatarEvidence.Add(sourceAvatar);
            avatarEvidence.AddRange(
                animators
                    .Where(animator => animator != null && animator.avatar != null)
                    .Select(animator => animator.avatar));
            var uniqueAvatarEvidence = avatarEvidence
                .Where(avatar => avatar != null)
                .GroupBy(avatar => avatar.GetInstanceID())
                .Select(group => group.First())
                .ToArray();

            int mappedHumanBones = 0;
            foreach (var avatar in uniqueAvatarEvidence.Where(item => item.isValid && item.isHuman))
            {
                try
                {
                    var human = avatar.humanDescription.human;
                    mappedHumanBones = Math.Max(mappedHumanBones, human != null ? human.Length : 0);
                }
                catch (InvalidOperationException) { }
            }

            reply.assetPath = assetPath;
            reply.animationType = importer.animationType.ToString();
            reply.avatarSetup = importer.avatarSetup.ToString();
            reply.sourceAvatarPresent = sourceAvatar != null;
            reply.sourceAvatarValid = sourceAvatar != null && sourceAvatar.isValid;
            reply.sourceAvatarHuman = sourceAvatar != null && sourceAvatar.isValid && sourceAvatar.isHuman;
            reply.avatarCount = avatars.Length;
            reply.avatarEvidenceCount = uniqueAvatarEvidence.Length;
            reply.validAvatarCount = uniqueAvatarEvidence.Count(avatar => avatar.isValid);
            reply.humanAvatarCount = uniqueAvatarEvidence.Count(avatar => avatar.isValid && avatar.isHuman);
            reply.humanoidMappedBoneCount = mappedHumanBones;
            reply.animationClipCount = clips.Length;
            reply.rootCurveClipCount = clips.Count(clip => clip.hasRootCurves);
            reply.motionCurveClipCount = clips.Count(clip => clip.hasMotionCurves);
            reply.humanMotionClipCount = clips.Count(clip => clip.humanMotion);
            reply.genericRootTransformClipCount = clips.Count(clip => clip.hasGenericRootTransform);
            reply.animatorCount = animators.Length;
            reply.animatorWithAvatarCount = animators.Count(animator => animator != null && animator.avatar != null && animator.avatar.isValid);
            reply.humanAnimatorCount = animators.Count(animator => animator != null && animator.avatar != null && animator.avatar.isValid && animator.avatar.isHuman);
            reply.meshRendererCount = meshRenderers.Length;
            reply.skinnedMeshRendererCount = skinnedRenderers.Length;
            reply.colliderCount = colliders.Length;
            reply.lodGroupCount = lodGroups.Length;
            reply.lodLevelCount = lodLevels.Count;
            reply.lodRendererCount = lodRendererCount;
            reply.lodEmptyLevelCount = lodEmptyLevelCount;
            reply.lodLevels = lodLevels.ToArray();
        }
    }
}
#endif
