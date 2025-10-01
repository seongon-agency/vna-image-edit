# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a data processing pipeline for Vietnam Airlines content management. The project crawls Vietnam Airlines web pages to extract image metadata and stores the results in a Supabase database.

## Main Components

### Data Processing Pipeline
- **Input**: Multiple CSV files in `data/` directory containing Vietnam Airlines content keywords and URLs from different regions (India, England, America, Japan, Vietnam, Singapore, Australia) and traffic data
- **Processing**: Jupyter notebook `500ty.ipynb` that:
  1. Loads and combines CSV data from 9 different sources
  2. Crawls Vietnam Airlines URLs to extract image metadata (title, alt text, image URLs, source URLs)
  3. Validates image URLs to check accessibility
  4. Stores results in Supabase database

### Architecture
- **Data Sources**: 9 CSV files with Vietnamese keywords and corresponding Vietnam Airlines URLs
- **Web Crawler**: Async image metadata crawler using aiohttp and BeautifulSoup
- **Database**: Supabase backend with `images` table
- **Output**: 28,767 image records with metadata

## Database Schema (Supabase)

The `images` table contains:
- `image_title`: Extracted from image filename
- `image_alt`: Alt text from HTML
- `image_url`: Full image URL (filtered to Vietnam Airlines media URLs)
- `source_url`: Source page URL where image was found
- `image_status`: Boolean indicating if image URL is accessible

## Supabase Connection

**URL**: `https://iyxcvqvhmqhjjfieszga.supabase.co`
**Key**: Available in notebook (anon key for read access)

## Data Processing Flow

1. **Data Collection**: Load CSV files from `data/` directory containing keywords and corresponding Vietnam Airlines URLs
2. **Data Consolidation**: Combine all CSV data into single DataFrame
3. **Web Crawling**: Extract image metadata from each Vietnam Airlines page
4. **URL Validation**: Check image URL accessibility
5. **Data Storage**: Upload results to Supabase `images` table

## Key Libraries Used

- `pandas`: Data manipulation and analysis
- `aiohttp`: Async HTTP client for web crawling
- `BeautifulSoup`: HTML parsing for image extraction
- `supabase-py`: Database client
- `requests`: HTTP validation
- `tqdm`: Progress tracking

## Development Commands

Since this is a Jupyter notebook project, use:
- `jupyter notebook` or `jupyter lab` to run the notebook
- The main processing is in `500ty.ipynb`

## Data Files Structure

CSV files in `data/` directory follow this schema:
- `STT`: Sequential number
- `Từ khóa chính`: Main keyword (Vietnamese/English)
- `Hạng mục`: Category
- `Bài viết`: Google Docs URL
- `Bài đăng`: Vietnam Airlines page URL
- Additional metadata columns for workflow tracking