#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wchar.h>
#include <stdbool.h>
#include <stdio.h>

#ifndef ORDAX_RUNTIME_LAUNCHER
#define ORDAX_RUNTIME_LAUNCHER 0
#endif

#define ORDAX_MAX_PATH 32768

static void fatal_message(const wchar_t *message) {
    MessageBoxW(NULL, message, L"ORDAX Studio", MB_OK | MB_ICONERROR | MB_SETFOREGROUND);
}

static bool get_install_root(wchar_t *root, DWORD capacity) {
    DWORD length = GetModuleFileNameW(NULL, root, capacity);
    if (length == 0 || length >= capacity) {
        return false;
    }
    wchar_t *slash = wcsrchr(root, L'\\');
    if (slash == NULL) {
        return false;
    }
    *slash = L'\0';
    return true;
}

static void set_default_environment(const wchar_t *name, const wchar_t *value) {
    if (GetEnvironmentVariableW(name, NULL, 0) == 0) {
        SetEnvironmentVariableW(name, value);
    }
}

static bool file_exists(const wchar_t *path) {
    DWORD attributes = GetFileAttributesW(path);
    return attributes != INVALID_FILE_ATTRIBUTES && !(attributes & FILE_ATTRIBUTE_DIRECTORY);
}

static HANDLE create_kill_job(void) {
    HANDLE job = CreateJobObjectW(NULL, NULL);
    if (job == NULL) {
        return NULL;
    }
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits;
    ZeroMemory(&limits, sizeof(limits));
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    if (!SetInformationJobObject(
            job,
            JobObjectExtendedLimitInformation,
            &limits,
            sizeof(limits))) {
        CloseHandle(job);
        return NULL;
    }
    return job;
}

static DWORD run_python_child(
    const wchar_t *python,
    const wchar_t *module,
    const wchar_t *root,
    HANDLE job,
    bool hidden
) {
    wchar_t command[ORDAX_MAX_PATH];
    if (_snwprintf_s(
            command,
            ORDAX_MAX_PATH,
            _TRUNCATE,
            L"\"%ls\" -m %ls",
            python,
            module) < 0) {
        return ERROR_INSUFFICIENT_BUFFER;
    }

    STARTUPINFOW startup;
    PROCESS_INFORMATION process;
    ZeroMemory(&startup, sizeof(startup));
    ZeroMemory(&process, sizeof(process));
    startup.cb = sizeof(startup);

    DWORD flags = CREATE_UNICODE_ENVIRONMENT;
    if (hidden) {
        flags |= CREATE_NO_WINDOW;
    }

    if (!CreateProcessW(
            NULL,
            command,
            NULL,
            NULL,
            FALSE,
            flags,
            NULL,
            root,
            &startup,
            &process)) {
        return GetLastError();
    }

    if (job != NULL) {
        AssignProcessToJobObject(job, process.hProcess);
    }

    WaitForSingleObject(process.hProcess, INFINITE);
    DWORD exit_code = 1;
    GetExitCodeProcess(process.hProcess, &exit_code);
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    return exit_code;
}

int APIENTRY wWinMain(HINSTANCE instance, HINSTANCE previous, LPWSTR command_line, int show) {
    (void)instance;
    (void)previous;
    (void)command_line;
    (void)show;

    const wchar_t *mutex_name = ORDAX_RUNTIME_LAUNCHER
        ? L"Local\\ORDAXRuntime"
        : L"Local\\ORDAXStudio";
    HANDLE mutex = CreateMutexW(NULL, TRUE, mutex_name);
    if (mutex == NULL) {
        fatal_message(L"Não foi possível inicializar a instância do ORDAX.");
        return 10;
    }
    if (GetLastError() == ERROR_ALREADY_EXISTS) {
        CloseHandle(mutex);
        return 0;
    }

    wchar_t root[ORDAX_MAX_PATH];
    wchar_t python[ORDAX_MAX_PATH];
    if (!get_install_root(root, ORDAX_MAX_PATH)) {
        fatal_message(L"Não foi possível localizar a instalação do ORDAX Studio.");
        CloseHandle(mutex);
        return 11;
    }

    const wchar_t *python_name = ORDAX_RUNTIME_LAUNCHER ? L"python.exe" : L"pythonw.exe";
    if (_snwprintf_s(
            python,
            ORDAX_MAX_PATH,
            _TRUNCATE,
            L"%ls\\runtime\\%ls",
            root,
            python_name) < 0 || !file_exists(python)) {
        fatal_message(L"O runtime privado do ORDAX Studio está ausente ou corrompido.");
        CloseHandle(mutex);
        return 12;
    }

    set_default_environment(L"ORDAX_PACKAGED_ROOT", root);
    set_default_environment(L"ORDAX_AGENT_REPO_PATH", root);
    set_default_environment(L"ORDAX_BRIDGE_PATH", root);
    SetCurrentDirectoryW(root);

    HANDLE job = create_kill_job();
    DWORD result = 0;

    if (!ORDAX_RUNTIME_LAUNCHER) {
        result = run_python_child(
            python,
            L"ordax_studio.web_desktop",
            root,
            job,
            false);
    } else {
        DWORD backoff_ms = 1000;
        for (;;) {
            ULONGLONG started = GetTickCount64();
            result = run_python_child(
                python,
                L"ordax_device_agent.main",
                root,
                job,
                true);
            ULONGLONG elapsed = GetTickCount64() - started;
            if (elapsed >= 60000) {
                backoff_ms = 1000;
            }
            Sleep(backoff_ms);
            if (backoff_ms < 30000) {
                backoff_ms *= 2;
                if (backoff_ms > 30000) {
                    backoff_ms = 30000;
                }
            }
        }
    }

    if (job != NULL) {
        CloseHandle(job);
    }
    ReleaseMutex(mutex);
    CloseHandle(mutex);
    return (int)result;
}
