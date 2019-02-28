#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 15 13:51:10 2019

@author: etsai
"""

import time
import os, sys
import re
import glob
from scipy import ndimage
from scipy import interpolate
from scipy.interpolate import griddata
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import random
import PIL.Image as Image
from skimage import color
from skimage import io

from fun_ky import *

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
    
    n = filename.find('*') # assume before this is the sample name
    
    temp = '*x{:.3f}*_y{:.3f}*'.format(xf, yf) 
    temp = filename[0:n-1]+temp # ignore char filename[n]
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
    log10 = feature_args['log10']
    feature_id = feature_args['feature_id']
    kwargs = feature_args['feature_{}_args'.format(feature_id)] 
    
    val = []    
    if feature_id == 1:
        pixels = kwargs['targets']
        roi = kwargs['roi']
        n = roi[0]
        im = color.rgb2gray(io.imread(infile))
        imarray = np.array(im)
        for pixel in pixels:
            temp_roi = imarray[pixel[1]-n:pixel[1]+n+1,pixel[0]-n:pixel[0]+n+1] #TEMP
            if roi[1]=='mean':
                temp = np.nanmean(temp_roi)
            elif roi[1]=='max':
                temp = np.nanmax(temp_roi) 
            else:
                temp = imarray[pixel[1], pixel[0]]
            if log10: temp = np.log10(temp)
            val.append(temp) 
        
    elif feature_id == 2:  
        data_col = kwargs['data_col']
        q_targets = kwargs['targets']
        roi = kwargs['roi']
        n = roi[0]
        q, I = extract_data(infile, data_col)
        for q_target in q_targets:
            cen = get_target_idx(q, q_target)
            if roi[1]=='mean':
                temp = np.nanmean(I[cen-n:cen+n+1]) 
            elif roi[1]=='max':
                temp = np.nanmax(I[cen-n:cen+n+1]) 
            else:
                temp = I[cen]                
            if log10: temp = np.log10(temp)
            val.append(temp) 

    elif feature_id == 3:  
        data_col = kwargs['data_col']
        angle_targets = kwargs['targets']
        angle_roi = kwargs['angle_roi']
        angle, I = extract_data(infile, data_col)
        i0 = get_target_idx(angle, angle_roi[0])
        i1 = get_target_idx(angle, angle_roi[1])
        I_crop = I[i0:i1+1]
        for angle_target in angle_targets:  
            temp = np.nan
            if angle_target =='max':
                if np.var(I_crop) > 0: # TEMP 
                    temp = angle[i0+np.nanargmax(I_crop)]
            elif angle_target =='var':
                temp = np.nanvar(I_crop)
            else: 
                try:
                    temp = I[get_target_idx(angle, angle_target)]
                    if log10: temp = np.log10(temp)
                except:
                    print('Cannot find I[get_target_idx(angle, angle_target)] \n')
            val.append(temp)   

    elif feature_id == 4:  
        xml_file = '{}{}{}'.format(kwargs['source_dir'], infile[len(kwargs['source_dir']):-4], '.xml' )
        try:
            result = fit_result(xml_file)
            print(result)
            val.append(result['fit_peaks_grain_size'])
        except:
            val.append(np.nan)

    info = [feature_id, kwargs['targets']]
                
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
#   features_map, including:
#       scans: list of scans (not sure how useful yet)
#       x_pos
#       y_pos
#       feature
# =============================================================================
def get_map(infiles, match_re, feature_args):
    scans = []
    x_pos = []
    y_pos = []
    features = []
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

    features = np.asarray(features)
    features = (features.T).tolist()
    features_map = {'scans': scans, 'x_pos':x_pos, 'y_pos':y_pos, 'features':features, 
                   'info':info, 'filename': filename}
    
    return features_map
    
    
# =============================================================================
# Plot one data
# =============================================================================        
def plot_data(infile, **feature_args):
    if 'log10' in feature_args:
        log10 = feature_args['log10']
    else:
        log10 = 0
    if 'feature_id' in feature_args:
        feature_id = feature_args['feature_id']
    else:
        feature_id = 1
        
    kwargs = feature_args['feature_{}_args'.format(feature_id)] 

    if 'cmap' in feature_args and feature_args['cmap']:
        cmap = feature_args['cmap']
    else:
        cmap = 'viridis'
    
    if feature_id == 1:
        pixels = kwargs['targets']
        im = color.rgb2gray(io.imread(infile))
        if log10:
            im = np.log10(im)
        plt.imshow(im, cmap=cmap)
        plt.colorbar(shrink=0.8, aspect=24)
        for pixel in pixels:
            plt.plot(pixel[0],pixel[1], 'o', markersize=8, markeredgewidth=1, markeredgecolor='w', markerfacecolor='None')
        plt.title(infile)
        return im
    elif feature_id == 2: 
        q_targets = kwargs['targets']
        data_col = kwargs['data_col']
        roi = kwargs['roi']
        n = roi[0]
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
        plt.ylabel('log10(I)')
        plt.xlabel('q ($\AA$^-1)')
        plt.grid(b=True, which='major', color='k', linestyle='-', alpha=0.25)      
    elif feature_id == 3:  
        data_col = kwargs['data_col']
        angle_targets = kwargs['targets']
        angle_roi = kwargs['angle_roi']
        angle, I = extract_data(infile, data_col)
        if log10: I = np.log10(I)
        plt.plot(angle, I)  
        for idx, angle_target in enumerate(angle_targets):
            if angle_target =='max':
                i0 = get_target_idx(angle, angle_roi[0])
                i1 = get_target_idx(angle, angle_roi[1])
                plt.plot([angle[i0], angle[i1]], [0, 0])
                I_crop = I[i0:i1+1]
                val = angle[i0+np.argmax(I_crop)]
                plt.plot([val, val], [0, 3])
                plt.text(val, 3-idx*0.1, 'argmax='+str(np.round(val,2)))
            elif type(angle_target) is not str:
                plt.plot([angle_target, angle_target], [0, 0])
                plt.plot([angle_target, angle_target], [0, 3])
                plt.text(angle_target, 0.1+idx*0.1, '('+str(angle_target)+')')
        plt.grid(b=True, which='major', color='k', linestyle='-', alpha=0.25)
        plt.xlabel('$\chi$ (degree)')
        
    plt.title(infile)
 
# =============================================================================
# Plot map based on feature
# =============================================================================       
def plot_map(feature_map, **kwargs):
    filename = feature_map['filename']
    feature_id = feature_map['info'][0]
    targets = feature_map['info'][1]
    x_pos = feature_map['x_pos']
    y_pos = feature_map['y_pos']
    features = feature_map['features']
    if 'val_stat' in kwargs:
        val_stat = kwargs['val_stat']
    if 'cmap' in kwargs and kwargs['cmap']:
        cmap = kwargs['cmap'];
    else:
        cmap = plt.get_cmap('viridis')
    if 'plot_interp' in kwargs:
        plot_interp = kwargs['plot_interp']
    else:
        plot_interp = ['none', 1]
    
    N_maps = len(features)
#    fig = plt.figure(100+feature_id, figsize=[20,4]); plt.clf()
    for idx, feature in enumerate(features):
        ax = plt.subplot2grid((1, N_maps+1), (0, idx+1), colspan=1); 
        feature = np.asarray(feature)
        val_stat = [np.nanmin(feature), np.nanmax(feature)]
        if plot_interp[0]!='none':
            x_pos_fine, y_pos_fine, feature_fine = interp_map(x_pos, y_pos, feature, plot_interp) 
            #plt.pcolormesh(x_pos_fine, y_pos_fine, feature_fine, vmin=val_stat[0], vmax=val_stat[1], cmap=cmap) 
            extent = (np.nanmin(x_pos_fine), np.nanmax(x_pos_fine), np.nanmin(y_pos_fine), np.nanmax(y_pos_fine))
            plt.imshow(feature_fine, vmin=val_stat[0], vmax=val_stat[1], extent=extent, origin='lower')
        else:
            plt.scatter(x_pos, y_pos, c=features[:,idx], marker="s", vmin=val_stat[0], vmax=val_stat[1], cmap=cmap) 
            
        plt.colorbar(shrink=1, pad=0.02, aspect=24);
        plt.grid(b=True, which='major', color='k', linestyle='-', alpha=0.25)
        #plt.title(source_dir+filename)
        plt.axis('equal')
        plt.xlabel('x (mm)  [feature_id '+ str(feature_id) + ',  ' + str(targets[idx])+']')
        plt.ylabel('y (mm)')
    
# =============================================================================
# Give interpolated map with finer discretization
# note - griddata works better than interpolate.interp2d
# =============================================================================          
def interp_map(x_pos, y_pos, feature, plot_interp): 
    x_ax_fine = np.arange(np.min(x_pos), np.max(x_pos), plot_interp[1]) 
    y_ax_fine = np.arange(np.min(y_pos), np.max(y_pos), plot_interp[1])
    x_pos_fine, y_pos_fine = np.meshgrid(x_ax_fine, y_ax_fine)
    feature_fine = griddata((x_pos, y_pos), feature, (x_pos_fine, y_pos_fine), method=plot_interp[0])
    return x_pos_fine, y_pos_fine, feature_fine

# =============================================================================
# Overlay three features
# =============================================================================       
def plot_overlay(feature_map_list, **kwargs):
    feature_array = []
    for ii, feature_map in enumerate(feature_map_list):
        if ii==0:
            x_pos = feature_map['x_pos']
            y_pos = feature_map['y_pos']
        features = feature_map['features']
        for feature in features:
            feature_array.append(feature)
        
    if 'plot_interp' in kwargs:
        plot_interp = kwargs['plot_interp']
    else:
        plot_interp = ['linear', 1] 
    
    overlay = []        
    if feature_array!=[]:
        fig = plt.figure(200, figsize=[8,8]); plt.clf()
        ax = fig.add_subplot(1, 1, 1)
        #ax.set_facecolor((0, 0, 0))
        ax.set_facecolor((1, 1, 1))
          
        for idx, feature in enumerate(feature_array):
            feature = np.asarray(feature)
            x_pos_fine, y_pos_fine, feature_fine = interp_map(x_pos, y_pos, feature, plot_interp) 
            feature_fine = (feature_fine-np.nanmin(feature_fine)) / (np.nanmax(feature_fine)-np.nanmin(feature_fine))
            feature_fine[np.isnan(feature_fine)] = 1 #np.nanmean(feature_fine)
            if idx<=2:
                overlay.append(feature_fine)
            else:
                print('More then 3 features, only use the first three for RGB')
     
        while idx<2:
            overlay.append(feature_fine*0.0)
            idx = idx+1
        overlay = np.asarray(overlay)
        overlay = np.transpose(overlay, (1,2,0))
        extent = (np.nanmin(x_pos_fine), np.nanmax(x_pos_fine), np.nanmin(y_pos_fine), np.nanmax(y_pos_fine))
        plt.imshow(overlay, extent=extent,origin='lower')
        
        #plt.colorbar(shrink=1, pad=0.02, aspect=24);
        plt.grid(b=True, which='major', color='k', linestyle='-', alpha=0.3)
        plt.axis('tight')
        plt.axis('equal')
        plt.xlabel('x (mm)')
        plt.ylabel('y (mm)')
    else:
        print('feature_array is empty!\n')
    return overlay

    
    