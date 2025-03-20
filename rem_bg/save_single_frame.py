import h5py
import numpy as np
import matplotlib.pyplot as plt

# Path to your large HDF5 file
file_path = '/home/bubl3932/files/glycine/batch_1640000_1649999/batch_1640000_1649999.h5'

with h5py.File(file_path, 'r') as f:
    # Access the dataset with diffraction images
    images = f['/entry/data/images']
    print("Dataset shape:", images.shape)
    # Extract the 4th frame (using index 3 if zero-indexed)
    frame4 = images[3]

vmin=0
vmax=30
# Save the 4th frame as a PNG image
plt.imsave("/home/bubl3932/files/glycine_frame4.png", frame4, cmap='gray', origin='lower', vmin=vmin, vmax=vmax)
print("Frame saved as frame4.png")

with h5py.File(file_path, 'r') as f:
    images = f['/entry/data/images']
    frame4 = images[3]

np.save("/home/bubl3932/files/glycine_frame4.npy", frame4)
print("Frame saved as frame4.npy")
