import csv

def read_metric_csv(csv_path, group_by_event=True):
    """
    Reads a CSV of metrics, keeping 'event_number' as a string.
    Skips rows like:  "Event number: 0-1,,,,,,," (if those exist).
    Parses known metric columns as floats (including negative values).
    
    NOTE: This version does NOT expect a 'combined_metric' column in the CSV.
    You can add or remove metrics from the parse list below as needed.

    Returns:
      - If group_by_event=True:
          A dictionary of { event_number_str -> list of row dicts }
      - If group_by_event=False:
          A flat list of row dicts.
    """

    rows = []
    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)

        for r in reader:
            # Some CSVs have lines that look like "Event number: 0-1,,,,,,,". Skip them:
            if r['stream_file'].startswith("Event number:"):
                continue

            # Keep event_number as a string. For example, "0-1", "1-1", etc.
            event_str = r['event_number']

            # Parse numeric metrics as floats, skipping rows that can't parse
            try:
                r['event_number']         = event_str  # e.g. "0-1"
                # The following lines parse your separate metrics
                r['weighted_rmsd']       = float(r['weighted_rmsd'])
                r['fraction_outliers']    = float(r['fraction_outliers'])
                r['length_deviation']     = float(r['length_deviation'])
                r['angle_deviation']      = float(r['angle_deviation'])
                r['peak_ratio']           = float(r['peak_ratio'])
                r['percentage_unindexed'] = float(r['percentage_unindexed'])
            except (ValueError, KeyError):
                # This row doesn't have valid floats in the expected columns, skip it
                continue

            rows.append(r)

    if not group_by_event:
        return rows

    # Group rows by their (string) event_number
    grouped = {}
    for row in rows:
        evt_id = row['event_number']
        grouped.setdefault(evt_id, []).append(row)

    return grouped


def select_best_results_by_event(grouped_data, sort_metric='weighted_rmsd'):
    """
    Given a dict { event_number_str -> list of row dicts },
    return a flat list of the 'best' row (lowest `sort_metric`) per event.
    (You can change the default sort_metric if desired.)
    """
    best_list = []
    for evt_str, rowlist in grouped_data.items():
        # Pick the row with the smallest 'sort_metric'
        best = min(rowlist, key=lambda x: x[sort_metric])
        best_list.append(best)
    return best_list


def get_metric_ranges(rows, metrics=None):
    """
    Given a list of row dicts (all with the same keys),
    compute (min, max) for each metric in `metrics`.

    Returns a dict:
      {
        'weighted_rmsd': (min_val, max_val),
        'fraction_outliers': (min_val, max_val),
        ...
      }

    If `metrics` is None, uses a default list of known metrics.
    If a metric has no data in 'rows', defaults to (0.0, 1.0).
    """
    if not metrics:
        metrics = [
            'weighted_rmsd', 'fraction_outliers', 'length_deviation',
            'angle_deviation', 'peak_ratio', 'percentage_unindexed'
        ]

    ranges = {}
    for m in metrics:
        vals = [r[m] for r in rows if m in r]
        if len(vals) == 0:
            ranges[m] = (0.0, 1.0)  # Fallback
        else:
            mn = min(vals)
            mx = max(vals)
            ranges[m] = (mn, mx)
    return ranges


def create_combined_metric(rows, metrics_to_combine, weights, new_metric_name='combined_metric'):
    """
    Add a new metric to each row dict, which is a weighted sum of the given metrics.
      - rows: list of row dicts
      - metrics_to_combine: list of metric names, e.g. ['weighted_rmsd', 'peak_ratio', ...]
      - weights: list of floats, same length as metrics_to_combine
      - new_metric_name: name of the new metric in each row, default "combined_metric"

    This modifies the rows in-place (adding row[new_metric_name]).
    """
    for r in rows:
        weighted_sum = 0.0
        for m, w in zip(metrics_to_combine, weights):
            weighted_sum += r[m] * w
        r[new_metric_name] = weighted_sum


def filter_rows(rows, thresholds):
    """
    Filter a list of row dicts by threshold dict, e.g.:
      thresholds = { 'weighted_rmsd': 1.0, 'combined_metric': 0.5, ... }

    We keep the row if row[metric] <= threshold for all metrics in the dict.
    """
    def passes(r):
        for metric, thr in thresholds.items():
            if metric not in r:
                # If the metric doesn't exist in row, skip it or treat as fail
                return False
            if r[metric] > thr:
                return False
        return True

    return [r for r in rows if passes(r)]


def write_filtered_csv(rows, output_csv_path, metrics_to_write=None):
    """
    Write a CSV file containing only `rows`, with specified columns.

    If `metrics_to_write` is None, we'll write all keys found in the first row.
    """
    if not rows:
        print(f"No rows to write. Empty CSV created at: {output_csv_path}")
        with open(output_csv_path, 'w', newline='') as f:
            f.write("No data\n")
        return

    if metrics_to_write is None:
        # Gather all keys from the first row (assuming all rows have same keys):
        metrics_to_write = list(rows[0].keys())

    with open(output_csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=metrics_to_write)
        writer.writeheader()
        for r in rows:
            subset = {m: r.get(m, "") for m in metrics_to_write}
            writer.writerow(subset)

    print(f"Filtered CSV written to: {output_csv_path}")
