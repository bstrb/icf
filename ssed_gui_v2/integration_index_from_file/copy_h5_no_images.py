import h5py
import os

def copy_with_placeholder_fill(src, dst, placeholder_path="/entry/data/images", placeholder_value=0):
    """
    Recursively copy items from the source HDF5 file to the destination file.
    When encountering the dataset at placeholder_path, create a new dataset with the
    same shape and dtype, but using a fillvalue so that it does not actually store all
    placeholder data.
    """
    for key in src:
        src_item = src[key]
        item_path = src_item.name

        if item_path == placeholder_path:
            print(f"Creating placeholder dataset for: {item_path}")
            if isinstance(src_item, h5py.Dataset):
                shape = src_item.shape
                dtype = src_item.dtype
                # Create a dataset with the same shape and dtype, using a fillvalue.
                # Here, we also enable gzip compression for further file size reduction.
                dst_ds = dst.create_dataset(key, shape=shape, dtype=dtype,
                                            fillvalue=placeholder_value, compression="gzip")
                # Copy attributes
                for attr in src_item.attrs:
                    dst_ds.attrs[attr] = src_item.attrs[attr]
            elif isinstance(src_item, h5py.Group):
                dst.create_group(key)
            continue

        # Copy groups and datasets normally
        if isinstance(src_item, h5py.Group):
            print(f"Copying group: {item_path}")
            dst_group = dst.create_group(key)
            copy_with_placeholder_fill(src_item, dst_group, placeholder_path, placeholder_value)
        elif isinstance(src_item, h5py.Dataset):
            print(f"Copying dataset: {item_path}")
            src.copy(src_item.name, dst, name=key)

def main():
    source_file = "/home/bubl3932/files/UOX1/UOX_His_MUA_450nm_spot4_ON_20240311_0928.h5"  # update with your source file path
    dst_file = os.path.splitext(source_file)[0] + "_placeholder.h5"
    print(f"Destination file will be: {dst_file}")
    
    with h5py.File(source_file, "r") as src_h5, h5py.File(dst_file, "w") as dst_h5:
        copy_with_placeholder_fill(src_h5, dst_h5)

if __name__ == "__main__":
    main()


