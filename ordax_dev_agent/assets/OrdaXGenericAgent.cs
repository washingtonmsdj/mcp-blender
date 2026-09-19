#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

// Portable companion: no game-specific types, scene names or assets.
namespace OrdaX.EditorTools
{
    [InitializeOnLoad]
    public static class OrdaXGenericAgent
    {
        [Serializable] private class Command
        {
            public string id, action, outputPath, scenePath;
            public int width = 1280, height = 720;
        }
        [Serializable] private class Reply
        {
            public string id, summary, artifact, snapshotPath;
            public bool ok, compiling, playing;
            public string unityVersion = Application.unityVersion;
            public string protocol = "ordax-generic-v2";
            public int errorCount, warningCount;
            public string activeScene, renderPipeline;
            public int gameObjectCount, activeGameObjectCount;
            public int rigidbodyCount, colliderCount, meshColliderCount;
            public int rendererCount, cameraCount, lightCount, canvasCount;
            public int rigidbodyWithoutColliderCount, dynamicNonConvexMeshColliderCount;
            public string[] auditWarnings;
        }
        [Serializable] private class SceneObject
        {
            public string name, path;
            public bool active;
            public Vector3 position, scale;
        }
        [Serializable] private class Snapshot
        {
            public string capturedAtUtc, scene, camera;
            public bool playing, objectsTruncated;
            public int objectCount;
            public SceneObject[] objects;
        }
        private static string Root => Path.Combine(Directory.GetParent(Application.dataPath).FullName, "Library", "OrdaXAgent");
        private static double nextPoll;
        private static int errors, warnings;
        static OrdaXGenericAgent()
        {
            EditorApplication.update += Tick;
            Application.logMessageReceived += OnLog;
        }
        private static void OnLog(string message, string stack, LogType type)
        {
            if (type == LogType.Error || type == LogType.Exception || type == LogType.Assert) errors++;
            if (type == LogType.Warning) warnings++;
        }
        private static Reply State(string id, bool ok, string summary)
        {
            return new Reply { id = id, ok = ok, summary = summary,
                compiling = EditorApplication.isCompiling, playing = EditorApplication.isPlaying,
                errorCount = errors, warningCount = warnings };
        }
        private static void Write(string path, object value)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            string temporary = path + ".tmp";
            File.WriteAllText(temporary, JsonUtility.ToJson(value, true));
            if (File.Exists(path)) File.Replace(temporary, path, null);
            else File.Move(temporary, path);
        }
        private static void Tick()
        {
            if (EditorApplication.timeSinceStartup < nextPoll) return;
            nextPoll = EditorApplication.timeSinceStartup + 0.35;
            try
            {
                Write(Path.Combine(Root, "editor-presence.json"), State("presence", true, "Generic Unity companion ready"));
                if (EditorApplication.isCompiling || EditorApplication.isUpdating) return;
                string inbox = Path.Combine(Root, "inbox");
                Directory.CreateDirectory(inbox);
                var files = Directory.GetFiles(inbox, "*.json");
                Array.Sort(files, StringComparer.Ordinal);
                if (files.Length > 0) Process(files[0]);
            }
            catch (IOException) { /* Retry atomic file access next tick. */ }
        }
        private static void Process(string file)
        {
            Command command = null;
            string id = Path.GetFileNameWithoutExtension(file);
            if (!Guid.TryParseExact(id, "N", out _)) { File.Delete(file); return; }
            Reply reply;
            try
            {
                command = JsonUtility.FromJson<Command>(File.ReadAllText(file));
                File.Delete(file);
                if (command == null || command.id != id) throw new InvalidOperationException("Command ID mismatch");
                reply = State(id, true, "Completed");
                switch (command.action)
                {
                    case "health": reply.summary = "Generic companion ready"; break;
                    case "validate":
                        reply.ok = errors == 0;
                        reply.summary = "Editor ready; errors observed since companion reload: " + errors;
                        break;
                    case "play_start":
                    case "play_stop":
                        // Persist acknowledgment before a Play Mode domain reload.
                        reply.summary = "Play Mode transition requested";
                        Write(Path.Combine(Root, "responses", id + ".json"), reply);
                        EditorApplication.isPlaying = command.action == "play_start";
                        return;
                    case "capture": Capture(command, reply); break;
                    case "scene_open": OpenScene(command, reply); break;
                    case "scene_summary": SceneSummary(reply, false); break;
                    case "physics_audit": SceneSummary(reply, true); break;
                    default: throw new InvalidOperationException("Unsupported companion action: " + command.action);
                }
            }
            catch (Exception error) { reply = State(id, false, error.GetType().Name + ": " + error.Message); }
            Write(Path.Combine(Root, "responses", id + ".json"), reply);
        }
        private static void SceneSummary(Reply reply, bool physicsAudit)
        {
            var sceneObjects = Resources.FindObjectsOfTypeAll<GameObject>()
                .Where(go => go != null && go.scene.IsValid() && go.scene.isLoaded)
                .ToArray();
            var rigidbodies = Resources.FindObjectsOfTypeAll<Rigidbody>()
                .Where(rb => rb != null && rb.gameObject.scene.IsValid() && rb.gameObject.scene.isLoaded)
                .ToArray();
            var colliders = Resources.FindObjectsOfTypeAll<Collider>()
                .Where(col => col != null && col.gameObject.scene.IsValid() && col.gameObject.scene.isLoaded)
                .ToArray();
            var meshColliders = Resources.FindObjectsOfTypeAll<MeshCollider>()
                .Where(col => col != null && col.gameObject.scene.IsValid() && col.gameObject.scene.isLoaded)
                .ToArray();

            int rigidbodyWithoutCollider = 0;
            int dynamicNonConvexMeshCollider = 0;
            var auditWarnings = new List<string>();

            foreach (var body in rigidbodies)
            {
                var attached = body.GetComponentsInChildren<Collider>(true);
                if (attached.Length == 0)
                {
                    rigidbodyWithoutCollider++;
                    auditWarnings.Add("Rigidbody without Collider: " + body.gameObject.name);
                }

                if (!body.isKinematic)
                {
                    foreach (var meshCollider in attached.OfType<MeshCollider>())
                    {
                        if (!meshCollider.convex)
                        {
                            dynamicNonConvexMeshCollider++;
                            auditWarnings.Add("Dynamic Rigidbody uses non-convex MeshCollider: " + body.gameObject.name);
                        }
                    }
                }
            }

            var pipeline = GraphicsSettings.currentRenderPipeline;
            reply.ok = !physicsAudit || (rigidbodyWithoutCollider == 0 && dynamicNonConvexMeshCollider == 0);
            reply.summary = physicsAudit
                ? (reply.ok ? "Physics audit passed" : "Physics audit found issues")
                : "Scene summary ready";
            reply.activeScene = SceneManager.GetActiveScene().path;
            reply.renderPipeline = pipeline != null ? pipeline.GetType().Name : "Built-in";
            reply.gameObjectCount = sceneObjects.Length;
            reply.activeGameObjectCount = sceneObjects.Count(go => go.activeInHierarchy);
            reply.rigidbodyCount = rigidbodies.Length;
            reply.colliderCount = colliders.Length;
            reply.meshColliderCount = meshColliders.Length;
            reply.rendererCount = Resources.FindObjectsOfTypeAll<Renderer>()
                .Count(r => r != null && r.gameObject.scene.IsValid() && r.gameObject.scene.isLoaded);
            reply.cameraCount = Resources.FindObjectsOfTypeAll<Camera>()
                .Count(cam => cam != null && cam.gameObject.scene.IsValid() && cam.gameObject.scene.isLoaded);
            reply.lightCount = Resources.FindObjectsOfTypeAll<Light>()
                .Count(light => light != null && light.gameObject.scene.IsValid() && light.gameObject.scene.isLoaded);
            reply.canvasCount = Resources.FindObjectsOfTypeAll<Canvas>()
                .Count(canvas => canvas != null && canvas.gameObject.scene.IsValid() && canvas.gameObject.scene.isLoaded);
            reply.rigidbodyWithoutColliderCount = rigidbodyWithoutCollider;
            reply.dynamicNonConvexMeshColliderCount = dynamicNonConvexMeshCollider;
            reply.auditWarnings = auditWarnings.Take(200).ToArray();
        }

        private static void OpenScene(Command command, Reply reply)
        {
            if (string.IsNullOrWhiteSpace(command.scenePath) ||
                !command.scenePath.StartsWith("Assets/", StringComparison.Ordinal) ||
                !command.scenePath.EndsWith(".unity", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("scenePath must be a project-relative Assets/*.unity path");

            string projectRoot = Directory.GetParent(Application.dataPath).FullName;
            string fullPath = Path.GetFullPath(Path.Combine(projectRoot, command.scenePath));
            if (!fullPath.StartsWith(projectRoot, StringComparison.OrdinalIgnoreCase) || !File.Exists(fullPath))
                throw new InvalidOperationException("Scene does not exist inside the project");

            var active = SceneManager.GetActiveScene();
            if (active.IsValid() && active.isDirty)
                throw new InvalidOperationException("Active scene has unsaved changes");

            UnityEditor.SceneManagement.EditorSceneManager.OpenScene(command.scenePath, UnityEditor.SceneManagement.OpenSceneMode.Single);
            reply.summary = "Scene opened: " + command.scenePath;
        }

        private static string Hierarchy(Transform transform)
        {
            string path = transform.name;
            while (transform.parent != null) { transform = transform.parent; path = transform.name + "/" + path; }
            return path;
        }
        private static void Capture(Command command, Reply reply)
        {
            if (string.IsNullOrWhiteSpace(command.outputPath) || !Path.IsPathRooted(command.outputPath))
                throw new InvalidOperationException("Capture needs an absolute output path");
            Camera camera = Camera.main;
            if (camera == null) camera = Camera.allCameras.FirstOrDefault();
            if (camera == null) throw new InvalidOperationException("No active scene camera; create or enable one");
            int width = Mathf.Clamp(command.width, 64, 3840), height = Mathf.Clamp(command.height, 64, 2160);
            var target = RenderTexture.GetTemporary(width, height, 24);
            var previousTarget = camera.targetTexture;
            var previousActive = RenderTexture.active;
            Texture2D image = null;
            try
            {
                camera.targetTexture = target;
                camera.Render();
                RenderTexture.active = target;
                image = new Texture2D(width, height, TextureFormat.RGB24, false);
                image.ReadPixels(new Rect(0, 0, width, height), 0, 0);
                image.Apply();
                Directory.CreateDirectory(Path.GetDirectoryName(command.outputPath));
                File.WriteAllBytes(command.outputPath, image.EncodeToPNG());
            }
            finally
            {
                camera.targetTexture = previousTarget;
                RenderTexture.active = previousActive;
                if (image != null) UnityEngine.Object.DestroyImmediate(image);
                RenderTexture.ReleaseTemporary(target);
            }
            var transforms = Resources.FindObjectsOfTypeAll<Transform>()
                .Where(t => t.gameObject.scene.IsValid() && t.gameObject.scene.isLoaded).ToArray();
            var snapshot = new Snapshot { capturedAtUtc = DateTime.UtcNow.ToString("o"),
                scene = SceneManager.GetActiveScene().path, camera = camera.name,
                playing = EditorApplication.isPlaying, objectCount = transforms.Length,
                objectsTruncated = transforms.Length > 1000,
                objects = transforms.Take(1000).Select(t => new SceneObject { name = t.name,
                    path = Hierarchy(t), active = t.gameObject.activeInHierarchy,
                    position = t.position, scale = t.lossyScale }).ToArray() };
            reply.artifact = command.outputPath;
            reply.snapshotPath = Path.ChangeExtension(command.outputPath, ".json");
            Write(reply.snapshotPath, snapshot);
            reply.summary = "Scene camera captured with hierarchy snapshot (screen-space overlay UI excluded)";
        }
    }
}
#endif
