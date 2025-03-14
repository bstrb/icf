# Define function for combined metric calculation using sum of metric value multiplied by its weight
def calculate_combined_metric(index, all_metrics, metric_weights):
    combined_metric = 0  # Start with 0 for summation
    for metric, weight in metric_weights.items():
        metric_value = all_metrics[metric][index]
        combined_metric += metric_value * weight
    return combined_metric
