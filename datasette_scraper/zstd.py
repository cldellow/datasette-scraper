import zstandard

DICT_SIZE = 112640
NUM_SAMPLES = 100

no_dict_compressor = zstandard.ZstdCompressor(level=9)
no_dict_decompressor = zstandard.ZstdDecompressor()

def get_dict(conn, dict_id):
    rv = conn.execute('SELECT dict FROM dss_zstd_dict WHERE id = ?', [dict_id]).fetchone()
    if not rv:
        raise Exception('unknown zstd dict_id {}'.format(dict_id))

    return zstandard.ZstdCompressionDict(rv[0])

def get_active_dict_id(conn, host):
    row = conn.execute('SELECT id FROM dss_zstd_dict WHERE active AND host = ? ORDER BY id DESC LIMIT 1', [host]).fetchone()

    if not row:
        return None

    dict_id, = row
    return dict_id

def get_compressor(conn, dict_id):
    if not dict_id:
        return no_dict_compressor

    return zstandard.ZstdCompressor(level=9, dict_data=get_dict(conn, dict_id))

def get_decompressor(conn, dict_id):
    if not dict_id:
        return no_dict_decompressor

    return zstandard.ZstdDecompressor(dict_data=get_dict(conn, dict_id))

def train_zstd_dict(conn, host):
    def get_samples(conn):
        hashes = conn.execute('SELECT object, dict_id FROM dss_fetch_cache WHERE host = ? ORDER BY RANDOM() LIMIT {}'.format(NUM_SAMPLES), [host]).fetchall()

        rv = []
        for (obj, dict_id) in hashes:
            decompressor = get_decompressor(conn, dict_id)
            rv.append(decompressor.decompress(obj))

        return rv

    samples = get_samples(conn)

    zdict = zstandard.train_dictionary(DICT_SIZE, samples)

    with conn:
        rv = conn.execute('INSERT INTO dss_zstd_dict(host, active, dict) VALUES (?, 1, ?)', [host, zdict.as_bytes()])
        return rv.lastrowid
