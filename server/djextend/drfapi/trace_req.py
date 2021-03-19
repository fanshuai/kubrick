import pendulum


def trace_request(request, **kwargs):
    now = pendulum.now()
    trace_time = now.timestamp()
    trace_data = dict(
        now=now.replace(microsecond=0).isoformat(),
        ruid=getattr(request, 'ruid', None),
    )
    start_time = getattr(request, 'req_start_time')
    use_ms = int(round(1e3 * (trace_time - start_time)))
    trace_data.update(use=use_ms)
    trace_data.update(kwargs)
    return trace_data
