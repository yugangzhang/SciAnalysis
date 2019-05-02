#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Imports
########################################

import sys, os
SciAnalysis_PATH='/home/kyager/current/code/SciAnalysis/main/'
SciAnalysis_PATH in sys.path or sys.path.append(SciAnalysis_PATH)

import glob
import numpy as np
import re

from SciAnalysis import tools
from SciAnalysis.Data import *
#from SciAnalysis.XSAnalysis.Data import *
#from SciAnalysis.XSAnalysis import Protocols


# Settings
########################################
verbosity = 3
pattern = 'PWM_sample_AM3' # Files to consider
source_dir = '../' # The location of the SciAnalysis outputs
output_dir = './{}/'.format(pattern)
tools.make_dir(output_dir)





# Helpers
########################################

filename_re = re.compile('(.+)_x(-?\d+\.\d+)_yy(-?\d+\.\d+)_.+_(\d+)_saxs\.xml')
def parse_filename(filename, verbosity=3):
    
    parsed = {'filename' : filename}
    m = filename_re.match(filename)
    if m:
        parsed['basename'] = m.groups()[0]
        parsed['x'] = float(m.groups()[1])
        parsed['y'] = float(m.groups()[2])
        parsed['scan_id'] = int(m.groups()[-1])
        
    else:
        if verbosity>=2:
            print("WARNING: RE doesn't match for {}".format(filename))
    
    return parsed
    

def val_stats(values, name='z'):
    span = np.max(values)-np.min(values)
    print("  {} = {:.2g} ± {:.2g} (span {:.2g}, from {:.2g} to {:.2g})".format(name, np.average(values), np.std(values), span, np.min(values), np.max(values)))
    


# Extract results from xml files
########################################
from SciAnalysis.Result import * # Results() object
def extract_results(infiles, outfile, verbosity=3):
    if verbosity>=3:
        print("Extracting results for {} infiles...".format(len(infiles)))
    
    extractions = [ [ 'metadata_extract', ['x_position', 'y_position', 'sequence_ID'] ] ,
                ['circular_average_q2I', ['fit_peaks_prefactor1', 'fit_peaks_x_center1', 'fit_peaks_sigma1', 'fit_peaks_chi_squared', 'fit_peaks_d0', 'fit_peaks_grain_size' ] ],
                ]    
    results = Results().extract_multi_save_txt(outfile, infiles, extractions, verbosity=verbosity)
    
    return results




# Plot
########################################

def load_results(infile, x_coord, y_coord, z_signal, sequence, verbosity=3):
    
    # Load results
    x_vals = []
    y_vals = []
    z_vals = []
    seq_vals = []
    with open(infile) as fin:
        names = fin.readline().split()
        
        if verbosity>=3:
            print(" Loading data from file: {}".format(infile))
        if verbosity>=4:
            print('Saved data has {} columns:'.format(len(names)))
            print(names)
            
        signal_idx = names.index(z_signal)
        x_idx = names.index(x_coord)
        y_idx = names.index(y_coord)
        sequence_idx = names.index(sequence)
        
        if verbosity>=3:
            print(" Plot signal: {} (column index {})".format(z_signal, signal_idx))
            print(" Plot x: {} (column index {})".format(x_coord, x_idx))
            print(" Plot y: {} (column index {})".format(y_coord, y_idx))
            print(" Sorting: {} (column index {})".format(sequence, sequence_idx))
            
        
        for line in fin.readlines():
            els = line.split()
            if len(els)==len(names) and els[0][0]!='#':
                x_vals.append(float(els[x_idx]))
                y_vals.append(float(els[y_idx]))
                z_vals.append(float(els[signal_idx]))
                seq_vals.append(int(float(els[sequence_idx])))
            else:
                if verbosity>=3:
                    print('  Skipping line: {}'.format(line.strip()))
                
        
    if verbosity>=3:
        print(" Nx, Ny, Nz = {}, {}, {}".format(len(x_vals), len(y_vals), len(z_vals)))
        val_stats(z_vals, name='z')

        
    # Sort data
    indices = np.argsort(seq_vals)
    x_vals = np.asarray(x_vals)[indices]
    y_vals = np.asarray(y_vals)[indices]
    z_vals = np.asarray(z_vals)[indices]
    seq_vals = np.asarray(seq_vals)[indices]
    
    return x_vals, y_vals, z_vals, seq_vals


def trim_vals(vals_list, N_max, verbosity=3):
    
    trimmed_vals_list = []
    for i, vals in enumerate(vals_list):
        if N_max is not None and len(vals)>N_max:
            if verbosity>=4:
                print(' Reducing list {} to size N_max = {}'.format(i, N_max))
            vals = np.asarray(vals)[:N_max]
        trimmed_vals_list.append(vals)
        
    return trimmed_vals_list
    
    
import SciAnalysis.colormaps as cmaps
plt.register_cmap(name='viridis', cmap=cmaps.viridis)
plt.register_cmap(name='magma', cmap=cmaps.magma)
plt.register_cmap(name='inferno', cmap=cmaps.inferno)
plt.register_cmap(name='plasma', cmap=cmaps.plasma)
plt.set_cmap(cmaps.viridis)    

class Data2D_current(Data2D):
    def _plot_extra(self, **plot_args):
        
        xi, xf, yi, yf = self.ax.axis()
        
        # Faded overlay
        rect = mpl.patches.Rectangle((xi,yi), xf-xi, yf-yi, linewidth=1, edgecolor='none', facecolor='white', alpha=self.alpha, zorder=10)
        self.ax.add_patch(rect)            
        
        
        # Scatterplot
        cmap = plot_args['cmap'] if 'cmap' in plot_args else 'viridis'
        zmin = plot_args['zmin']
        zmax = plot_args['zmax']
        self.ax.scatter(self.x_vals, self.y_vals, s=100, c=self.z_vals, cmap=cmap, vmin=zmin, vmax=zmax, edgecolor='k', zorder=100)
        
        
        # Colorbar
        n = 5
        colorbar_labels = [ zmin + i*(zmax-zmin)/(n-1) for i in range(n) ]
        
        tick_positions = self._plot_z_transform(data=colorbar_labels, set_Z=False)
        cbar = self.fig.colorbar(self.im, ax=self.ax, ticks=tick_positions, fraction=0.056, pad=0.02)
        colorbar_labels = ["{:.3g}".format(c) for c in colorbar_labels]
        cbar.ax.set_yticklabels(colorbar_labels, size=20)                
        
    def _plot_extra3D(self, **plot_args):
        cbar = self.fig.colorbar(self.surf, ax=self.ax, aspect=40, fraction=0.02, pad=0.0)
        cbar.ax.yaxis.set_tick_params(labelsize=15)
    
    
    
def plot_results(x_vals, y_vals, z_vals, outfile, plot2d=True, plot3d=False, grid=None, dgrid=None, title=None, cmap='viridis', alpha=0.5, verbosity=3):
    
    # Define grid for interpolation
    if grid is None:
        grid = [np.min(x_vals), np.max(x_vals), np.min(y_vals), np.max(y_vals)]
    if dgrid is None:
        dgrid = [ (grid[1]-grid[0])/200 , (grid[3]-grid[2])/200 ]
    if isinstance(dgrid, float):
        dgrid = [dgrid, dgrid]
        
    xi = np.arange(grid[0], grid[1]+dgrid[0], dgrid[0])
    yi = np.arange(grid[2], grid[3]+dgrid[1], dgrid[1])
    XI, YI = np.meshgrid(xi, yi)


    # Interpolation
    import scipy.interpolate
    POINTS = np.column_stack((x_vals,y_vals))
    VALUES = z_vals
    if verbosity>=3:
        print("Interpolating {:,} points to {:,}×{:,} = {:,} points".format(len(VALUES), len(xi), len(yi), len(xi)*len(yi)))    
        
    ZI = scipy.interpolate.griddata(POINTS, VALUES, (XI, YI), method='linear') # method='nearest' 'linear' 'cubic'
    ZI_mask = np.ma.masked_where( np.isnan(ZI), ZI)

    if verbosity>=3:
        val_stats(ZI, name='ZI')
        val_stats(ZI_mask, name='ZI_mask')
    
    d = Data2D_current()
    d.data = ZI_mask
    d.x_axis = xi
    d.y_axis = yi
    
    d.x_vals = x_vals
    d.y_vals = y_vals
    d.z_vals = z_vals


    d.set_z_display([None, None, 'linear', 1.0])
    d.x_rlabel = '$x \, (\mathrm{mm})$'
    d.y_rlabel = '$y \, (\mathrm{mm})$'
    
    if plot2d:
        d.plot_args['rcParams'] = { 
                        'axes.labelsize': 50,
                        'xtick.labelsize': 40,
                        'ytick.labelsize': 40,    
                        }
        d.alpha = alpha

        
        d.plot(save=outfile, show=False, cmap=cmap, zmin=zmin, zmax=zmax, title=title, plot_buffers=[0.21, 0.12, 0.18, 0.10], plot_range=grid, plot_2D_type='pcolormesh', dpi=150, transparent=False)
    
    
    if plot3d:
        d.plot_args['rcParams'] = { 
                        'axes.labelsize': 40,
                        'xtick.labelsize': 20,
                        'ytick.labelsize': 20,    
                        }    
        d.X = XI
        d.Y = YI
        #outfile = outfile[:-4]+'-3D.png'
        outfile = tools.Filename(outfile).path_append('3D')
        d.plot3D(save=outfile, show=False, cmap=cmap, zmin=zmin, zmax=zmax, title=title, plot_buffers=[0.05, 0.10, 0.05, 0.05], plot_range=grid, elev=30, azim=30-90, dpi=150, transparent=False)
    

def plot_grids(results, N_list, n_grid=200, plot2d=True, plot3d=False, cmap='viridis', verbosity=3):
    
    x_vals, y_vals, z_vals, seq_vals = results
    
    # Set size/shape of interpolation grid based on the full dataset
    n_grid = [n_grid, n_grid]
    grid = [np.min(x_vals), np.max(x_vals), np.min(y_vals), np.max(y_vals)]
    dgrid = [ (grid[1]-grid[0])/n_grid[0] , (grid[3]-grid[2])/n_grid[1] ]
    
    
    #N_list = [len(z_vals)] # Plot final value only
    
    for N in N_list:
        x_vals, y_vals, z_vals, seq_vals = trim_vals(results, N_max=N, verbosity=verbosity)
        if verbosity>=3:
            val_stats(z_vals, name='z_reduced')    
            
        outfile = os.path.join(output_dir, signal, '{}-{}-N{:04d}.png'.format(pattern, signal, N))
        title = '$N = {:,d}$'.format(N)
        plot_results(x_vals, y_vals, z_vals, outfile=outfile, plot2d=plot2d, plot3d=plot3d, grid=grid, dgrid=dgrid, title=title, cmap=cmap, alpha=0.2, verbosity=verbosity)
    
        

def animated_gif(source_dir='./', pattern='*.png', outfile=None, skip=None, verbosity=3):
    if verbosity>=3:
        print('Generating animated gif for {}/{}'.format(source_dir, pattern))
        
    # Select the files to animate
    infiles = glob.glob(os.path.join(source_dir, pattern))
    if verbosity>=3:
        print('    {} infiles'.format(len(infiles)))
        
        
    infiles.sort()
        
    if skip is not None:
        infiles = infiles[0::skip]
        
        
    if outfile is None:
        outfile = os.path.join(source_dir, 'anim.gif')
    elif outfile[-4:]!='.gif':
        outfile = outfile+'.gif'

    # Prepare command
    # (Animation is generated using imagemagick 'convert' bash command.)

    #cmd = "convert -delay 20 -resize 50% -fill white  -undercolor '#00000080'  -gravity NorthWest -annotate +0+5 ' Text ' "
    #cmd = "convert -delay 15 -loop 1 -resize 50% "
    #cmd = "convert -crop 450x450+60+220  +repage -delay 15 -loop 1 -resize 50% "
    cmd = "convert -dispose previous +repage -delay 30 -loop 1 -resize 30% "
            
    for infile in infiles:
        cmd += '{} '.format(infile)
    
    cmd += ' {}'.format(outfile)

    # Execute command
    print('  Saving {}'.format(outfile))
    os.system(cmd)
    
    # Add a white background
    #cmd = 'convert {} -coalesce -background white -alpha remove {}'.format(outfile, outfile[:-4]+'w.gif')
    #os.system(cmd)
    
    
    
    
# Run
########################################
    
# Extract results from XML files
results_dir = source_dir + '/results/' # Location of xml files
infiles = glob.glob(os.path.join(results_dir, '{}*.xml'.format(pattern)))
outfile = os.path.join(output_dir, '{}-extracted.txt'.format(pattern))

#results = extract_results(infiles, outfile=outfile, verbosity=verbosity)


# Plot results
x_coord = 'metadata_extract__x_position'
y_coord = 'metadata_extract__y_position'
#z_signal, zmin, zmax, cmap = 'circular_average_q2I__fit_peaks_x_center1', 0.0129, 0.0138, 'viridis'
#z_signal, zmin, zmax, cmap = 'circular_average_q2I__fit_peaks_d0', 44, 49, 'viridis'
#z_signal, zmin, zmax, cmap = 'circular_average_q2I__fit_peaks_grain_size', 50, 300, 'inferno'
z_signal, zmin, zmax, cmap = 'circular_average_q2I__fit_peaks_prefactor1', 0.0005, 0.002, cmap_vge
sequence = 'metadata_extract__sequence_ID'

protocol, signal = z_signal.split('__')


def power_N_list(N_max, N_min=3, num=40, exponent=3.0):
    
    #N_list = ( (np.exp( np.linspace(0, 1, num=40) ) - 1)/(np.exp(1)-1) )*len(z_vals)
    x = np.linspace(0, 1, num=num)
    N_list = np.power(x, exponent)*(N_max-N_min) + N_min
    N_list = np.unique(N_list.astype(int))
    #N_list = N_list[ (N_list>=N_min) & (N_list<=N_max) ] # Unnecessary
    print(N_list)
    
    return N_list

if False:
    if verbosity>=3:
        print("Plotting...")
        
    tools.make_dir(os.path.join(output_dir,signal))
    tools.make_dir(os.path.join(output_dir,signal,'3D'))
    
    results = load_results(outfile, x_coord=x_coord, y_coord=y_coord, z_signal=z_signal, sequence=sequence, verbosity=verbosity)
    x_vals, y_vals, z_vals, seq_vals = results
    
    # Single result
    #plot_grids(results, [len(z_vals)], n_grid=200, plot2d=True, plot3d=False, cmap=cmap, verbosity=verbosity)
    #plot_grids(results, [len(z_vals)], n_grid=40, plot2d=False, plot3d=True, cmap=cmap, verbosity=verbosity)

    # 2D plots
    N_spacing = 50
    N_list = np.arange(N_spacing, len(z_vals), N_spacing)
    #N_list = power_N_list(len(z_vals), num=40, exponent=5.0)
    plot_grids(results, N_list, n_grid=200, plot2d=True, plot3d=False, cmap=cmap, verbosity=verbosity)
    
    # 3D plots
    #plot_grids(results, N_list, n_grid=40, plot2d=False, plot3d=True, cmap=cmap, verbosity=verbosity)
    
    
    

    
if True:
    outfile = os.path.join(output_dir, '{}-{}.gif'.format(pattern, signal))
    animated_gif(source_dir=os.path.join(output_dir, signal), outfile=outfile, verbosity=verbosity)

    outfile = os.path.join(output_dir, '{}-{}-3D.gif'.format(pattern, signal))
    #animated_gif(source_dir=os.path.join(output_dir, signal, '3D'), outfile=outfile, verbosity=verbosity)




    