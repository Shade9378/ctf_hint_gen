import shlex
import subprocess


class DockerExecutor:
    def __init__(self, container_name: str, cwd: str = "/challenge"):
        self.container_name = container_name
        self.cwd = cwd

    def run(self, cmd: str) -> dict:
        script = f"""
cd {shlex.quote(self.cwd)} 2>/dev/null || cd /challenge
{cmd}
rc=$?
printf '\\n__LOGGER_EXIT_CODE__:%s\\n' "$rc"
printf '__LOGGER_PWD__:%s\\n' "$PWD"
"""

        result = subprocess.run(
            ["docker", "exec", self.container_name, "bash", "-lc", script],
            capture_output=True,
            text=True,
        )

        raw_stdout = result.stdout
        stderr = result.stderr

        exit_code = None
        new_cwd = self.cwd
        output_lines = []

        for line in raw_stdout.splitlines():
            if line.startswith("__LOGGER_EXIT_CODE__:"):
                try:
                    exit_code = int(line.split(":", 1)[1])
                except ValueError:
                    exit_code = None
            elif line.startswith("__LOGGER_PWD__:"):
                new_cwd = line.split(":", 1)[1]
            else:
                output_lines.append(line)

        self.cwd = new_cwd

        output = "\n".join(output_lines)

        if stderr.strip():
            output = output + ("\n" if output else "") + stderr.strip()

        return {
            "cmd": cmd,
            "output": output,
            "exit_code": exit_code,
            "cwd": self.cwd,
            "container": self.container_name,
        }