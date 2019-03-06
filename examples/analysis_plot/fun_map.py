#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 15 13:51:10 2019

@author: etsai
"""

import time, os, sys, re, glob, random, copy
import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage
from scipy import interpolate
from scipy.interpolate import griddata
from matplotlib.colors import ListedColormap
import PIL.Image as Image
from skimage import color
from skimage import io

from fun_ky import *
import lmfit

from mpl_toolkits.axes_grid1 import host_subplot
import mpl_toolkits.axisartist as AA
        
# =============================================================================
# Load data from .dat 
# - Extract columns col[0] and col[1]
# =============================================================================   
def extract_data(filename, col):
    infile = open(filename, 'r')
    infile.readline() # skip the first line
    q = []
    I = []
    for line in infile:
        data = line.split()
        q.append(float(data[col[0]]))
        I.append(float(data[col[1]]))
    infile.close()
    return q, I

# =============================================================================
# Get files with matching dir, filename, ext
# - Depending on feature_id, it loads the corresponding args and files
# - sort: scan number (better implementation?)
# ============================================================================= 
def get_filematch(feature_args):
    filename = feature_args['filename']  
    exclude = feature_args['exclude']
    feature_id = feature_args['feature_id']
    verbose = feature_args['verbose']
    kwargs = feature_args['feature_{}_args'.format(feature_id)]        
    source_dir = kwargs['source_dir']
    ext = kwargs['ext']

    pattern = filename+'*'+ext
    print(pattern)
    infiles = glob.glob(os.path.join(source_dir, pattern))
    infiles.sort()
    #infiles.sort(key=lambda name: int(name[-15:-9]))  #key=lambda x:float(re.findall("(\d+)",x)[0])
    
    #parse_re = '^.+_x(-?\d+\.\d+)_y(-?\d+\.\d+)_.+_SAXS{}$'.format(ext)
    if feature_args['map_type']=='xy':
        parse_re = '^.+_x(-?\d+\.\d+)_y(-?\d+\.\d+)_.+_(\d+)_\w+{}$'.format(ext)
    elif feature_args['map_type']=='xT':
        parse_re = '^.+_x(-?\d+\.\d+)_T(-?\d+\.\d+)_.+_(\d+)_\w+{}$'.format(ext)
    else:
        print('Specify map type (eg. xy, T)!')
        match_re = [];
        return infilles, match_re
        
    match_re = re.compile(parse_re)    
    if verbose>0:
        print(pattern)
        print('Considering {} files...'.format(len(infiles)))   
    
    # Exclude some files
    for idx, infile in enumerate(infiles):
        for file in exclude:
            if infile.find(file)>-1:
                infiles.pop(idx)
    if verbose>0:
        print('  - Now considering {} files...'.format(len(infiles)))   
            
    return infiles, match_re

# =============================================================================
# Get files with matching pattern
# ============================================================================= 
def get_filematch_s(pattern):
    infiles = glob.glob(pattern)
    infiles.sort()  
    parse_re = '^.+_x(-?\d+\.\d+)_y(-?\d+\.\d+)_.+_(\d+)$'
    match_re = re.compile(parse_re)      
    return infiles

# =============================================================================
# Given x y position, find the file
# =============================================================================
def find_file(xf, yf, feature_args):
    filename = feature_args['filename']
    feature_id = feature_args['feature_id']
    kwargs = feature_args['feature_{}_args'.format(feature_id)] 
    source_dir = kwargs['source_dir']
    ext = kwargs['ext']
    
    n = filename.find('*') # assume before this is the sample name
    
    temp = '*x{:.3f}*_y{:.3f}*'.format(xf, yf) 
    temp = filename[0:n-3]+temp+ext  # ignore some char
    pattern = os.path.join(source_dir, temp) 
    infiles = get_filematch_s(pattern)
    return infiles

# =============================================================================
# Given x,y and a list of data positions, find the closest point with data
# =============================================================================
def get_closest(pos, post_list):# pos_list is 2 by N
    r_min = 1e10;
    for idx, item in enumerate(post_list[0]):
        x = post_list[0][idx]
        y = post_list[1][idx]
        r = calc_distance(pos, [x, y])
        if r<r_min:
            r_min = r
            xf = x; yf = y
            #idxf = int(idx)
    return xf, yf

# =============================================================================
# Calculate distance between 2 Cartersian points
# =============================================================================
def calc_distance(p0, p1):
    r =  math.hypot(p0[0]-p1[0], p0[1]-p1[1])
    return r

# =============================================================================
#
# Define features! 
#
# =============================================================================
def get_feature(infile, feature_args):
    log10 = feature_args['log10'][0]
    feature_id = feature_args['feature_id']
    kwargs = feature_args['feature_{}_args'.format(feature_id)] 
    
    val = []; info = [] # additional infor to store 
    if feature_id == 1:
        pixels = kwargs['targets']
        roi = kwargs['roi']
        n = roi[0]
        #im = color.rgb2gray(io.imread(infile)); imarray = np.array(im)
        im = np.load(infile).items()
        imarray = np.array(im[0][1])        
        
        if log10: imarray = np.log10(imarray)
        for pixel in pixels:
            temp_roi = imarray[pixel[1]-n:pixel[1]+n+1,pixel[0]-n:pixel[0]+n+1] #TEMP
            if roi[1]=='mean':
                temp = np.nanmean(temp_roi)
            elif roi[1]=='max':
                temp = np.nanmax(temp_roi) 
            else:
                temp = imarray[pixel[1], pixel[0]]
            val.append(temp)
        
    elif feature_id == 2:  
        data_col = kwargs['data_col']
        q_targets = kwargs['targets']
        roi = kwargs['roi']
        n = roi[0]
        #t1 = time.time()
        q, I = extract_data(infile, data_col)
        if log10: I = np.log10(I)
        #print('time.f2 = {}'.format(time.time()-t1))
        for q_target in q_targets:
            cen = get_target_idx(q, q_target)
            if roi[1]=='mean':
                temp = np.nanmean(I[cen-n:cen+n+1]) 
            elif roi[1]=='max':
                temp = np.nanmax(I[cen-n:cen+n+1]) 
            else:
                temp = I[cen] 
            val.append(temp)
        
    elif feature_id == 3:  
        data_col = kwargs['data_col']
        angle_targets = kwargs['targets']
        angle_roi = kwargs['angle_roi']
        N = kwargs['N_fold']
        angle, I = extract_data(infile, data_col)
        angle_fold, I_fold_stat = line_fold(angle, I, N)
        I_fold = I_fold_stat[:,1] #mean
        if log10: 
            I = np.log10(I)
            I_fold = np.log10(I_fold)
        i0 = get_target_idx(angle, angle_roi[0])
        i1 = get_target_idx(angle, angle_roi[1])
        I_crop = I[i0:i1+1]
        for angle_target in angle_targets:  
            temp = np.nan
            if angle_target =='max':
                temp = angle_fold[np.nanargmax(I_fold)]
                #if np.var(I_crop) > 0: # TEMP 
                #    temp = angle[i0+np.nanargmax(I_crop)]
            elif angle_target =='var':
                temp = np.nanvar(I_crop)
            else: 
                try:
                    temp = I_fold[get_target_idx(angle_fold, angle_target)]
                    #temp = I[get_target_idx(angle, angle_target)]
                except:
                    print('Cannot find I[get_target_idx(angle, angle_target)] \n')
            val.append(temp)

    elif feature_id == 4:  
        data_col = kwargs['data_col']
        feats = kwargs['targets']
        q, I = extract_data(infile, data_col) 
        if log10: I = np.log10(I)
        line = DataLine(x=q, y=I)
        run_args = {'fit_range': [0.02, 0.06], 'sigma': 0.001, 'verbosity': 0}
        lm_result, fit_line, fit_line_extended = Protocols.circular_average_q2I_fit()._fit_peaks(line=line, q0=None, vary=True, **run_args)
        for feat in feats:
            if feat == 'd_spacing_nm':
                temp = 0.1*2.*np.pi/lm_result.params['x_center1'] #d in nm
            elif feat == 'grain_size_nm':
                temp = 0.1*(2.*np.pi/np.sqrt(2.*np.pi))/lm_result.params['sigma1'] #nm
            elif feat == 'chi2':
                temp = lm_result.chisqr/lm_result.nfree
            else:
                temp = lm_result.params[feat]  
            val.append(temp)
        info.append(line)
        info.append(fit_line)
            
    return val, info


# =============================================================================
# Get the index (for array q) closest to q_target
# =============================================================================  
def get_target_idx(q, target):
    q = np.array(q)
    idx = np.argmin(np.abs(q-target))
    return idx


# =============================================================================
# get_map(infiles, match_re, feature_args)
#
# Fill the map on coordinates x, y, with the feature
# Calls "get_feature" for each file
#
# Inputs: 
#   infiles: file list
#   match_re: extract positions x, y, and scan ID
#   feature_args: which feature, what specifics
# Outputs:
#   features_map:
#       scans: list of scans (not sure how useful yet)
#       x_pos
#       y_pos
#       tag: [id, feature_names]
#       features: for each feature_id, there can be several features
# =============================================================================
def get_map(infiles, match_re, feature_args):
    filename = feature_args['filename']
    feature_id = feature_args['feature_id']
    kwargs = feature_args['feature_{}_args'.format(feature_id)] 
    ids = []
    tags = []
    scans = []
    x_pos = []
    y_pos = []
    features = [] 
    info_map = []
    
    for target in kwargs['targets']:
        ids.append(feature_id) 
        tags.append(target) 
 
    for idx, infile in enumerate(infiles):
           
        filebase, filename = os.path.split(infile)
        m = match_re.match(filename)
        
        if m!=None:
            x = float(m.groups()[0]) 
            y = float(m.groups()[1]) # note: y is sometimes off by 0.5um because filename has only 3 decimal
            scan = int(m.groups()[2]) # scan number
            x_pos.append(x)
            y_pos.append(y)
            scans.append(scan)
    
            val, info = get_feature(infile, feature_args) # val can be an array
            features.append(val)
            if info: info_map.append(info)

    features = np.asarray(features)
    features = (features.T).tolist()
    features_map = {'ids': ids, 'tags': tags, 'scans': scans, 'x_pos':x_pos, 'y_pos':y_pos, 'features':features, 
                   'info_map':info_map, 'filename': filename}
    
    return features_map
    
    
# =============================================================================
# Plot one data
# =============================================================================        
def plot_data(infile, **feature_args):
    font = {'family' : 'normal',
        'weight' : 'bold',
        'size'   : 12}
    
    if 'log10' in feature_args:
        log10 = feature_args['log10'][1]
    else:
        log10 = 0
    if 'feature_id' in feature_args:
        feature_id = feature_args['feature_id']
    else:
        feature_id = 1
    verbose = feature_args['verbose']        
    kwargs = feature_args['feature_{}_args'.format(feature_id)] 

    if 'cmap' in feature_args and feature_args['cmap']:
        cmap = feature_args['cmap']
    else:
        cmap = 'viridis'
       
    result = []
    if feature_id == 1:
        pixels = kwargs['targets']
        im = np.load(infile).items()
        imarray = im[0][1] #image
        x_axis = im[1][1] 
        y_axis = im[2][1] 
        x_scale = im[3][1] 
        y_scale = im[4][1] 
        extent = (np.nanmin(x_axis), np.nanmax(x_axis), np.nanmin(y_axis), np.nanmax(y_axis))
        if log10:
            imarray = np.log10(imarray)        
        
        #plt.imshow(imarray, extent=extent, cmap=cmap, origin='lower')     
        host = host_subplot(111,axes_class=AA.Axes)
        plt.subplots_adjust(right=0.8)       
        host.imshow(imarray, cmap=cmap, origin='lower') # vmin=val_stat[0], vmax=val_stat[1]    
        #plt.colorbar(shrink=0.8, aspect=24)
        for pixel in pixels:
            host.plot(pixel[0],pixel[1], 'o', markersize=8, markeredgewidth=1, markeredgecolor='w', markerfacecolor='None')
        
        par2 = host.twinx()
        new_fixed_axis = par2.get_grid_helper().new_fixed_axis
        par2.axis["right"] = new_fixed_axis(loc="right",
                                            axes=par2,
                                            offset=(10, 0))
        par2.axis["right"].toggle(all=True)
        par2.set_ylabel("q ($\AA^{-1}$)", color='k')
        par2.set_ylim(extent[2],extent[3])
        par2.tick_params(axis='y', colors='k', grid_color='r', labelcolor='r')
        par2.spines['left'].set_color('r')

        result = imarray
        
    elif feature_id == 2: 
        q_targets = kwargs['targets']
        data_col = kwargs['data_col']
        if 'roi' in kwargs:
            n = kwargs['roi'][0]
        else:
            n = 0
        q, I = extract_data(infile, data_col)        
        if log10: I = np.log10(I)
        plt.plot(q, I)     
        for idx, q_target in enumerate(q_targets):
            if type(q_target) is not str:
                plt.plot([q_target, q_target], [-1, 4])
                plt.text(q_target, -0.9+idx*0.5, '('+str(q_target)+')')
                # plot integration region
                cen = get_target_idx(q, q_target)
            plt.plot([q[cen-n], q[cen+n]], [-1, -1]) 
        plt.xlabel('q ($\AA$^-1)')
        plt.grid(b=True, which='major', color='k', linestyle='-', alpha=0.25)  
        if log10: 
            plt.ylabel('log10(I)')
        else:
            plt.ylabel('Intensity (a.u.)')
   
    elif feature_id == 3:  
        data_col = kwargs['data_col']
        angle_targets = kwargs['targets']
        angle_roi = kwargs['angle_roi']
        angle, I = extract_data(infile, data_col)
        if log10: I = np.log10(I)
        plt.plot(angle, I)  
        y_lim = [np.nanmin(I), np.nanmax(I)]
        for idx, angle_target in enumerate(angle_targets):
            if angle_target =='max':
                i0 = get_target_idx(angle, angle_roi[0])
                i1 = get_target_idx(angle, angle_roi[1])
                plt.plot([angle[i0], angle[i1]], [y_lim[0], y_lim[0]])
                I_crop = I[i0:i1+1]
                val = angle[i0+np.argmax(I_crop)]
                plt.plot([val, val], y_lim)
                plt.text(val, np.max(I_crop)*0.95, 'argmax='+str(np.round(val,2)))
            elif type(angle_target) is not str:
                plt.plot([angle_target, angle_target], [y_lim[0], y_lim[0]])
                plt.plot([angle_target, angle_target], y_lim)
                plt.text(angle_target, y_lim[0]+idx*0.1, '('+str(angle_target)+')')
        plt.grid(b=True, which='major', color='k', linestyle='-', alpha=0.25)
        plt.xlabel('$\chi$ (degree)')
        if log10: 
            plt.ylabel('log10(I)')
        else:
            plt.ylabel('Intensity (a.u.)')
            
    elif feature_id == 4:
        feats = kwargs['targets']
        val, info = get_feature(infile, feature_args)
        for line in info:
            I = np.log10(line.y)
            plt.plot(line.x, I) 
        
        ys = np.nanmin(I)
        yf = np.nanmax(I)
        space = yf*0.11
        xs = np.min(line.x)
        xf = np.max(line.x)*0.9
        for idx, feat in enumerate(feats):
            temp = np.asarray(val[idx]) #Note - type(val[0])=lmfit.parameter.Parameter; val[idx].value
            plt.text(xf, yf-space*idx, feat+'={:.3f}'.format(temp), **font)
        plt.ylim([ys*0.3, yf*1.2])
        plt.xlim([xs*0.5, xf*1.5])
        plt.xlabel('q ($\AA$^-1)')
        plt.grid(b=True, which='major', color='k', linestyle='-', alpha=0.25)
        
    if verbose: 
        ll = len(infile)
        l0 = int(np.round(ll/3))
        plt.title(infile[0:l0]+'\n'+infile[l0+1:l0*2]+'\n'+infile[l0*2+1:-1])
                
    return result
 
# =============================================================================
# Plot map based on feature
# =============================================================================       
def plot_map(features_map, **kwargs):
    if 'filename' in features_map:
        filename = features_map['filename']
    else:
        filename = ''
    if 'ids' in features_map:
        ids = features_map['ids']
    else:
        print('WHY no ids?')
        return
    if 'tags' in features_map:
        tags = features_map['tags']
    else:
        print('WHY no tags?')
        return
    x_pos = features_map['x_pos']
    y_pos = features_map['y_pos']
    features = features_map['features']
    if 'log10' in kwargs:
        log10 = kwargs['log10'][1]
    else:
        log10 = 0
    if 'val_stat' in kwargs:
        val_stat = kwargs['val_stat']
    if 'cmap' in kwargs and kwargs['cmap']:
        cmap = kwargs['cmap'];
    else:
        cmap = plt.get_cmap('viridis')
    if 'plot_interp' in kwargs:
        plot_interp = kwargs['plot_interp']
    else:
        plot_interp = [None, 1]
    
    N_maps = len(features)
    for idx, feature in enumerate(features):
        ax = plt.subplot2grid((1, N_maps), (0, idx), colspan=1); 
        feature = np.asarray(feature)
        if log10:
            feature = np.log10(feature)
        if 'val_stat' not in kwargs:
            #val_stat = [np.nanmin(feature), np.mean([np.nanmedian(feature), np.nanmax(feature)]) ]
            val_stat = [np.nanmin(feature), np.nanmax(feature)]
        if plot_interp[0] is not None:
            #print('Plotting map using imshow')
            x_pos_fine, y_pos_fine, feature_fine = interp_map(x_pos, y_pos, feature, plot_interp) 
            #plt.pcolormesh(x_pos_fine, y_pos_fine, feature_fine, vmin=val_stat[0], vmax=val_stat[1], cmap=cmap) 
            extent = (np.nanmin(x_pos_fine), np.nanmax(x_pos_fine), np.nanmin(y_pos_fine), np.nanmax(y_pos_fine))
            plt.imshow(feature_fine, vmin=val_stat[0], vmax=val_stat[1], extent=extent, origin='lower')
        else:
            #print('Plotting map using scatter')
            plt.scatter(x_pos, y_pos, c=feature, marker="s", vmin=val_stat[0], vmax=val_stat[1], cmap=cmap) 
            
        plt.colorbar(shrink=1, pad=0.02, aspect=24);
        plt.grid(b=True, which='major', color='k', linestyle='-', alpha=0.25)
        #plt.title(source_dir+filename)
        plt.title('Map {}'.format(idx))
        plt.axis('equal')
        plt.xlabel('x (mm)  [feature_id '+ str(ids[idx]) + ',  ' + str(tags[idx])+']')
        plt.ylabel('y (mm)')
    
# =============================================================================
# Give interpolated map with finer discretization
# Note - griddata works better than interpolate.interp2d
# =============================================================================          
def interp_map(x_pos, y_pos, feature, plot_interp): 
    x_ax_fine = np.arange(np.min(x_pos), np.max(x_pos), plot_interp[1]) 
    y_ax_fine = np.arange(np.min(y_pos), np.max(y_pos), plot_interp[1])
    x_pos_fine, y_pos_fine = np.meshgrid(x_ax_fine, y_ax_fine)
    feature_fine = griddata((x_pos, y_pos), feature, (x_pos_fine, y_pos_fine), method=plot_interp[0])
    return x_pos_fine, y_pos_fine, feature_fine

# =============================================================================
# Overlay three features (RGB)
#   features_map_list: list of feautres_maps, with len = # of feature ids
#   features = feature_map['features']: 1D or 2D array, axes are [postision, feature]
#   feature in features: 1D array, axis is [position]
#   feature_array: list of 1D or 2D arrays, from all the feature_ids, [postision, feature]
#
#   Example of features_map_list[0]['tag']:  
#       [4, ['b', 'prefactor1', 'd_spacing_nm', 'grain_size_nm', 'chi2']]
# =============================================================================       
def plot_overlay(features_map_list, **kwargs):
    if 'overlay_rgb' in kwargs:
        overlay_rgb = kwargs['overlay_rgb']
    else:
        overlay_rgb = [0, 1, 2]
    if 'normalize_each' in kwargs:
        normalize_each = kwargs['normalize_each']
    else:
        normalize_each = True
    if 'log10' in kwargs:
        log10 = kwargs['log10'][1]    
    else:
        log10 = 0
    if 'plot_interp' in kwargs:
        plot_interp = kwargs['plot_interp']
        if plot_interp[0] is None:
            plot_interp[0] = 'linear' 
    else:
        plot_interp = ['linear', 1] 
         
    ## Get all the maps into one 2D array, feature_array
    features_map = extract_maps(features_map_list)
    x_pos = features_map['x_pos']
    y_pos = features_map['y_pos']
    feature_array = features_map['features']
    ids = features_map['ids']
    tags = features_map['tags']
    
    ## Take three channels for plotting
    overlay = []; overlay_legend = [] ; channel = 0; rgb = 'RGB'
    if feature_array!=[]:
        fig = plt.figure(500, figsize=[10, 8]); plt.clf()
        
        ## Get max and min for normalization 
        max_val = -1; min_val = 1e15;
        for ii, feature in enumerate(feature_array):
            if ii in overlay_rgb:
                if np.nanmax(feature_array[ii]) > max_val:
                    max_val = np.nanmax(feature_array[ii])
                if np.nanmin(feature_array[ii]) < min_val:
                    min_val = np.nanmin(feature_array[ii])
          
        ## Take three channels, interpolate to fine grid
        if len(feature_array)>3: 
            print('More then 3 features available, using only {} for RGB'.format(overlay_rgb))
        for ii, feature in enumerate(feature_array):
            if ii in overlay_rgb:
                feature = np.asarray(feature)
                if log10: feature = np.log10(feature)
                x_pos_fine, y_pos_fine, feature_fine = interp_map(x_pos, y_pos, feature, plot_interp) 
                if normalize_each:
                    feature_fine = (feature_fine-np.nanmin(feature_fine)) / (np.nanmax(feature_fine)-np.nanmin(feature_fine)) # Normalize each channel
                else:
                    feature_fine = (feature_fine-min_val) / (max_val-min_val) # Normalize wrt max_val 
                feature_fine[np.isnan(feature_fine)] = 0  # Replace nan 

                ## Plot each channel                
                ax = plt.subplot2grid((3, 7), (channel, 0), colspan=2); 
                image_channel = np.asarray(image_RGB(feature_fine, rgb[channel]))
                if overlay==[]:
                    overlay = image_channel
                    extent = (np.nanmin(x_pos_fine), np.nanmax(x_pos_fine), np.nanmin(y_pos_fine), np.nanmax(y_pos_fine))
                else: 
                    overlay += image_channel
                plt.imshow(image_channel, extent=extent, origin='lower') 
                plt.title('({}) id={}, {}'.format(rgb[channel], ids[ii], tags[ii]))
                channel += 1
        
        ## Plot with imshow
        ax = plt.subplot2grid((3, 7), (0, 2), rowspan=3, colspan=4); ax.cla()
        ax.set_facecolor('k')
        plt.imshow(overlay, extent=extent,origin='lower')        
        plt.title('normalize_each {}'.format(normalize_each))
        plt.grid(b=True, which='major', color='k', linestyle='-', alpha=0.3)
        plt.axis('tight')
        plt.axis('equal')
        plt.xlabel('x (mm)')
        #plt.ylabel('y (mm)')
        
        ## Plot the colorcone
        ax2 = plt.subplot2grid((3, 7), (0, 6), colspan=1); ax2.cla()
        colorbar = Image.open('hsl_cone_graphic.jpg')
        plt.imshow(colorbar)
        plt.axis('off')
    else:
        print('feature_array is empty!\n')
    return overlay

# =============================================================================
# 
# =============================================================================
def image_RGB(image, rgb):
    dim = image.shape
    image_stack = np.zeros([dim[0], dim[1], 3])    
    if 'R' in rgb:
        image_stack[:,:,0] = image
    if 'G' in rgb:
        image_stack[:,:,1] = image     
    if 'B' in rgb:
        image_stack[:,:,2] = image
    
    return image_stack


# =============================================================================
# Extract maps from all feature_ids
# Example:
#    features_map, legends = extract_maps(features_map_list)
# Input:
#   features_map_list: list of feautres_maps, with len = # of feature ids
#       features = feature_map['features']: 1D or 2D array, axes are [postision, feature]
#       feature in features: 1D array, axis is [position]
# Output: 
#   features_map (see output of get_map)
#       x_pos, x_pos, tag
#       feature_array: list of 1D or 2D arrays, from all the feature_ids, [postision, feature]
# =============================================================================
def extract_maps(features_map_list):
    feature_array = []; 
    ids = []  # feature_id
    tags = [] # feature name
    for ii, feature_map in enumerate(features_map_list): # ii the index for feature_ids
        if ii==0:
            x_pos = feature_map['x_pos']
            y_pos = feature_map['y_pos']
        features = feature_map['features']  # 2D map
        for jj, feature in enumerate(features):  # jj the index for each features within each feature_id
            feature_array.append(feature)
            ids.append(features_map_list[ii]['ids'][jj])
            tags.append(features_map_list[ii]['tags'][jj])
   
    # Repack into features_map (good/bad?)
    features_map = {}
    features_map.update(x_pos=x_pos, y_pos=y_pos, features=feature_array)
    features_map.update(ids=ids, tags=tags)
    
    return features_map


# =============================================================================
# Do math on two selected features
# Example (feature_c = feature_a/feature_b):
#   feature_args['math_ab'] = [0, 1, 'divide'] 
#   feature_c = math_features(features_map_list, **feature_args)
# Output:
#   feature_c: new feature map
#   features_map_list: updated (appended) with a new feature_id (100+ii) contianing the new feature_c map
# =============================================================================
def math_features(features_map_list, **kwargs):
    print('Apply math to features...')
    print('  - Current features_map_list len = {}'.format(len(features_map_list)))
    print('  - Current N_maps = {}'.format(count_maps(features_map_list)))
    feature_array = []; legends = []
    if 'math_ab' in kwargs:
        math_ab = kwargs['math_ab']
    else:
        math_ab = [1, 2, 'divide']
    if 'log10' in kwargs:
        log10 = kwargs['log10'][1]    
    else:
        log10 = 0
    if 'plot_interp' in kwargs:
        plot_interp = kwargs['plot_interp']
        if plot_interp[0] is None:
            plot_interp[0] = 'linear' 
    else:
        plot_interp = ['linear', 1] 
         
    ## Get all the maps into one 2D array, feature_array
    features_map = extract_maps(features_map_list)
    feature_array = features_map['features']
    tags = features_map['tags']

    feature_a = np.asarray(feature_array[math_ab[0]])
    feature_b = np.asarray(feature_array[math_ab[1]])
    if math_ab[2] == 'divide':
        feature_c = feature_a / feature_b
    elif math_ab[2] == 'substract':
        feature_c = feature_a - feature_b   
    elif math_ab[2] == 'multiply':
        feature_c = feature_a * feature_b
    elif math_ab[2] == 'correlation': ## change
        feature_c = np.corrcoef(feature_a, feature_b)  

    idx = len(features_map_list)-1
    current_id = int(np.asarray(features_map_list[idx]['ids'][0]))
    if current_id<100:
        math_id = 100
    else:
        math_id = current_id+1
    original_list = copy.deepcopy(features_map_list[idx])
    features_map_list.append(original_list)
    features_map_list[idx+1]['features'] = [feature_c] # see def get_map for features_map structure
    features_map_list[idx+1].update(ids=[math_id])
    temp = '({})({}){}, {}'.format(math_ab[0],math_ab[1],math_ab[2], tags[math_ab[0]])
    features_map_list[idx+1].update(tags=[temp])
    
    print('  - Current features_map_list len = {}'.format(len(features_map_list)))
    print('  - Current N_maps = {}'.format(count_maps(features_map_list)))
    
    return feature_c


# =============================================================================
# Count # of feature maps
# =============================================================================
def count_maps(features_map_list):
    N_maps = 0
    for ii, feature_map in enumerate(features_map_list): 
        N_maps += len(feature_map['features'])
        
    return N_maps


# =============================================================================
# Assume N symmetry
# =============================================================================
def line_fold(x, y, N):
    verbose = 1
    len0 = len(y)
    len1 = int(np.floor(len0/N))
    x_fold = np.asarray(x[0:len1])-np.min(x)
    y_fold = np.zeros([len1,4])
    for ii in np.arange(0, len1):
        val = []
        for nn in np.arange(0,N):
            idx = get_target_idx(x[ii]+360/N*nn, x)
            val.append(y[idx])
        y_fold[ii,0] = np.min(val)
        y_fold[ii,1] = np.mean(val)
        y_fold[ii,2] = np.max(val)
        y_fold[ii,3] = np.var(val)
    
    if verbose:
        plt.figure(24); plt.clf()
        for jj in [0,1,2,3]:
            ax = plt.subplot2grid((4,1), (jj,0))
            plt.plot(x_fold, y_fold[:,jj])
            plt.grid()
    
    return x_fold, y_fold






