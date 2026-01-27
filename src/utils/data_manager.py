import dvc.api
import pandas as pd
import io
from statsmodels.tsa.seasonal import seasonal_decompose

class DVCDataManager:
    """
    Handles data loading and preprocessing, leveraging DVC for version control.
    Now agnostic to column names: assumes Col 0 is Date, Col 1 is Target.
    """
    def __init__(self, repo_url: str = "."):
        # repo_url="." implies the local repository
        self.repo_url = repo_url

    def get_data_stream(self, file_path: str, rev: str | None = None) -> io.StringIO:
        """Streams data explicitly defined by a Git revision (rev) using the DVC API.

        Useful when reading from a remote repository history without downloading the full file.

        Args:
            file_path: Path to the file within the DVC repository.
            rev: Git commit hash (or tag) to retrieve data from.
                 Defaults to None (current workspace).

        Returns:
            An in-memory text stream (io.StringIO) of the file content.
        """
        print(f"--- Fetching data from DVC: {file_path} (rev={rev if rev else 'HEAD/Working Dir'}) ---")

        # dvc.api.read looks for the file in S3, referencing the dvc.lock in the passed rev
        data_content = dvc.api.read(
            path=file_path,
            repo=self.repo_url,
            rev=rev,
            mode='r',
            encoding='utf-8'
        )
        return io.StringIO(data_content)

    def load_and_preprocess(self, config: dict, dataset_path: str):
        """
        Generic Time Series Loader.

        Assumptions:
        1. The CSV has at least 2 columns.
        2. Column 0 contains Date/Time information.
        3. Column 1 contains the Numeric Target value.

        Args:
            config (dict): Configuration dictionary containing 'data' settings.
            dataset_path (str): Local path to the CSV file (usually provided by DVC cache).

        Returns:
            tuple[pd.Series, pd.Series]: Train and Test splits of the residuals.
        """
        print(f"--- Loading Data from: {dataset_path} ---")

        user_conf = config.get('user_parameters', {})
        data_conf = user_conf.get('data', {})
        model_conf = user_conf.get('model', {})

        df = pd.read_csv(dataset_path)

        if df.shape[1] < 2:
            raise ValueError(f"Dataset must have at least 2 columns. Found {df.shape[1]}")

        date_col = df.columns[0]
        value_col = df.columns[1]

        try:
            df[date_col] = pd.to_datetime(df[date_col])
        except Exception as e:
            raise ValueError(f"Failed to convert '{date_col}' to datetime: {e}")

        df.set_index(date_col, inplace=True)
        df.sort_index(inplace=True)
        ts = pd.to_numeric(df[value_col], errors='coerce').dropna()

        # Frequency from User Config
        freq = data_conf.get('frequency')
        if freq:
            try:
                ts.index.freq = freq
            except Exception:
                print(f"Warning: Could not force freq '{freq}'.")

        target_data = ts
        split_ratio = data_conf.get('split_ratio', 0.9)
        size = int(len(target_data) * split_ratio)
        return target_data.iloc[0:size], target_data.iloc[size:]
