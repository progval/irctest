import dataclasses
import gzip
import io
import json
from pathlib import Path
import sys
from typing import Iterator
import urllib.parse
import urllib.request
import zipfile


@dataclasses.dataclass
class Artifact:
    repo: str
    run_id: int
    name: str
    download_url: str

    @property
    def public_download_url(self):
        # GitHub API is not available publicly for artifacts, we need to use
        # a third-party proxy to access it...
        name = urllib.parse.quote(self.name)
        return f"https://nightly.link/{repo}/actions/runs/{self.run_id}/{name}.zip"


def iter_run_artifacts(repo: str, run_id: int) -> Iterator[Artifact]:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts",
        headers={"Accept": "application/vnd.github.v3+json"},
    )

    response = urllib.request.urlopen(request)

    for artifact in json.load(response)["artifacts"]:
        if not artifact["name"].startswith(("pytest_results_", "pytest results ")):
            continue
        if artifact["expired"]:
            continue
        yield Artifact(
            repo=repo,
            run_id=run_id,
            name=artifact["name"],
            download_url=artifact["archive_download_url"],
        )


def download_artifact(output_name: Path, url: str) -> None:
    if output_name.exists():
        return
    response = urllib.request.urlopen(url)
    archive_bytes = response.read()  # Can't stream it, it's a ZIP
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        with archive.open("pytest.xml") as input_fd:
            pytest_xml = input_fd.read()

    tmp_output_path = output_name.with_suffix(".tmp")
    with gzip.open(tmp_output_path, "wb") as output_fd:
        output_fd.write(pytest_xml)

    # Atomically write to the output path, so that we don't write partial files in case
    # the download process is interrupted
    tmp_output_path.rename(output_name)


def main(output_dir: Path, repo: str, run_id: int) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_path = output_dir / str(run_id)
    run_path.mkdir(exist_ok=True)

    for artifact in iter_run_artifacts(repo, run_id):
        artifact_path = run_path / artifact.name / "pytest.xml.gz"
        artifact_path.parent.mkdir(exist_ok=True)
        try:
            download_artifact(artifact_path, artifact.download_url)
        except Exception:
            download_artifact(artifact_path, artifact.public_download_url)
        print("downloaded", artifact.name)

    return 0


if __name__ == "__main__":
    (_, output_path, repo, run_id) = sys.argv
    exit(main(Path(output_path), repo, int(run_id)))
