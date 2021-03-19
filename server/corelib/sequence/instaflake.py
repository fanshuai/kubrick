"""
Django BigIntegerField, 64位:
    -9223372036854775808 to 9223372036854775807.

https://www.jianshu.com/p/e664ce409a25
https://darktea.github.io/notes/2013/12/08/Unique-ID
https://github.com/falcondai/python-snowflake/blob/master/snowflake.py
"""
import time
import random
import threading

# 63 位
timestamp_bits = 42  # 2 ** 42
shard_bits = 11  # 2 * 1024
seq_bits = 10  # 2**10 = 1024


max_timestamp_id = 1 << timestamp_bits
max_shard_id = 1 << shard_bits
max_seq_id = 1 << seq_bits

# Range 16 * 16
twepoch = 478296287225  # ! '2019-12-31T23:58:35+08:00
min_bid = 0x2000000000000000  # 2305843009213693952  # 2019-12
max_bid = 0x7fffffffffffffff  # 9223372036854775807  # 2124-07


def make_instaflake(ts_ms, shard_id, seq_id):
    """
    Generate a snowflake id
    """
    sid = ((int(ts_ms) - twepoch) % max_timestamp_id) << shard_bits << seq_bits
    sid += (shard_id % max_shard_id) << seq_bits
    sid += seq_id % max_seq_id
    return sid


def melt(flake_id):
    """
    Inversely transform a snowflake id back to its parts.
    """
    seq_id = flake_id & (max_seq_id - 1)
    shard_id = (flake_id >> seq_bits) & (max_shard_id - 1)
    ts_ms = flake_id >> seq_bits >> shard_bits
    ts_ms += twepoch
    return ts_ms, shard_id, seq_id


def bid_generator(seq_id=0, shard_id=0):
    """
    Big int id generator.
    """
    shard_id = shard_id or threading.currentThread().ident
    seq_id = seq_id or random.randint(1, max_seq_id)
    ts_ms = int(time.time() * 1000)
    bid = make_instaflake(ts_ms, shard_id, seq_id)
    assert min_bid < bid < max_bid, f'{bid} {ts_ms}-{shard_id}-{seq_id}'
    return bid


if __name__ == '__main__':
    import pendulum
    tt = int(time.time() * 1000)
    print(pendulum.from_timestamp(tt / 1000).in_tz('Asia/Shanghai'))
    assert(melt(make_instaflake(tt, 0, 0))[0] == tt)
