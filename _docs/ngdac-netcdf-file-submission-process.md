---
title: NGDAC NetCDF File Submission Process
wikiPageName: NGDAC-NetCDF-File-Submission-Process
keywords: IOOS, documentation
tags: [getting_started, about, overview]
toc: false
#search: exclude
#permalink: index.html
summary: This page provides a detailed description of the end-to-end process of becoming a data provider, registering new glider deployments and submitting NetCDF files to the U.S. IOOS National Glider Data Assembly Center.
---

<!--
> [Wiki](https://github.com/kerfoot/ioosngdac/wiki) ▸ **NGDAC File Submission Process**

# Contents

+ [Data Provider Registration](#data-provider-registration)
+ [New Deployment Registration](#new-deployment-registration)
+ [Submission of NetCDF Files](#submission-of-netcdf-files)
+ [Dataset Status](#dataset-status)
+ [Dataset Archiving](#dataset-archiving)
-->

Following a **thorough** reading, all additional questions/concerns/suggestions should be directed to:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[glider.dac.support@noaa.gov](mailto:glider.dac.support@noaa.gov?subject=GliderDAC%20Support)

A consolidated list of the links referenced below can be found [here](/ioosngdac/useful-links).


## Data Provider Registration

You must register as a data provider and receive a user account in order to contribute data sets to the **IOOS Glider Data Assembly Center**.  The following contact information is required:

 + Contact name
 + Contact organization
 + Email address
 + Telephone number

and all user account requests should be emailed to:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[glider.dac.support@noaa.gov](mailto:glider.dac.support@noaa.gov?subject=GliderDAC%20Support)

**New user accounts are typically created the same day they are received**.

## New Deployment Registration

Data providers can register deployments after the user account has been created.  New deployment registration is a 1 or 2 step process, depending on whether the deployment is current or historical.  If the deployment is current or in the future and you would like the data to be released on the **Global Telecommunication System (GTS)**, you must request a [WMO id](http://www.wmo.int/pages/prog/amp/mmop/buoy-ids.html) for the glider.  This ID must be referenced as a [global](ngdac-netcdf-file-format-version-2.html#description--examples-of-required-global-attributes) attribute as well as an attribute of the file's [platform](ngdac-netcdf-file-format-version-2.html#platform) variable in each NetCDF file uploaded to the **NGDAC**.

The next step is to register the deployment with the **NGDAC**.

### Requesting a WMO ID

In order for the datasets to be released to the [Global Telecommunication System](http://www.wmo.int/pages/prog/www/TEM/index_en.html), the glider must be assigned a **WMO ID**.  All **WMO ID** requests should be sent to:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[glider.dac.support@noaa.gov](mailto:glider.dac.support@noaa.gov?subject=WMO ID%20Request)

The following information must be provided for each request:
+ Data provider
+ Glider name
+ Approximate deployment date
+ Approximate deployment location (GPS coordinates)

Once the request is received, it will be forwarded to the [National Data Buoy Center](http://www.ndbc.noaa.gov/) and the assigned **WMO ID** will be sent to the requestor/data provider.

**IMPORTANT**: WMO ids are assigned based on the [WMO region](http://en.wikipedia.org/wiki/Location_identifier#WMO_station_identifiers) in which the glider is deployed.  Once assigned, the WMO id may be used on successive deployments of the same glider provided it is deployed in the same WMO region.  **You do not need to acquire a different WMO id each time the glider is deployed, provided it is deployed in the same WMO region.**

### Deployment Creation

Deployments are registered and managed via the [GliderDAC providers page](https://gliders.ioos.us/providers). Each deployment must be registered by the data provider **before** any NetCDF files are uploaded.  The deployment registration process is as follows:

1. Navigate to the [GliderDAC providers page](https://gliders.ioos.us/providers/) and login with your account credentials.
2. Click the **Your Deployments** link.  A deployment registration form will be displayed.

![GliderDAC - Deployments page](/ioosngdac/DAC_providers_your_deployments.png)

3. Enter the name of the glider and deployment date/time (ISO-8601) using the following convention:
    **YYYYmmddTHHMM**

    Where **YYYYmmddTHHMM** is the timestamp specifying  the start of the deployment.  This is also the value that should be assigned to the [trajectory](ngdac-netcdf-file-format-version-2.html#trajectory) variable in each NetCDF file that is submitted to the DAC.  

    **IMPORTANT**:
    This WMO id must be included as th [global](ngdac-netcdf-file-format-version-2.html#description--examples-of-required-global-attributes) attribute wmo_id as well as an attribute (wmo_id) of the file's [platform](ngdac-netcdf-file-format-version-2.html#platform) variable in each NetCDF file uploaded to the **NGDAC**.
    
4. An additional field, attribution, is also provided as a means for the data provider to acknowledge the funding agencies and/or funding source.

5. Click **New Deployment** to create the deployment.  This creates a directory on the IOOS Glider DAC FTP server using the specified deployment name.  This is the directory that the NetCDF files must be uploaded to.

    **IMPORTANT: New deployments cannot be created by logging into the ftp server.  All new deployments must be created via the process described above.**

6. After the deployment has been registered, click on the deployment name to take you to the deployment metadata page and specify the **operator**.  Once the deployment has been completed (i.e.: the glider has been recovered or the deployment has been completed), click the **Completed** check box to denote that the data is ready for archiving by [NCEI](http://www.ncei.noaa.gov). See the [section below](ngdac-netcdf-file-submission-process.html#dataset-archiving) for more details on the NCEI archival process.

## Submission of NetCDF Files

The data provider user account provides ftp push access to the directories created under the user's home directory.  The ftp url is:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`   ftp://gliders.ioos.us`

Here's an example of the ftp login process and the resulting directory structure:

```
    $ ftp -i gliders.ioos.us
    Connected to gliders.ioos.us (54.204.42.247).
    220 Welcome to the IOOS Glider DAC FTP Server
    Name (gliders.ioos.us:kerfoot): rutgers
    331 Please specify the password.
    Password:
    230 Login successful.
    Remote system type is UNIX.
    Using binary mode to transfer files.
    ftp> pwd
    257 "/"
    ftp> dir
    200 PORT command successful. Consider using PASV.
    150 Here comes the directory listing.
    drwxr-xr-x    2 ftp      ftp         77824 Dec 08 16:40 ru01-20140104T1621
    drwxr-xr-x    2 ftp      ftp          4096 Dec 08 16:41 ru01-20140120T1444
    drwxr-xr-x    2 ftp      ftp         57344 Dec 08 16:41 ru01-20140123T1250
    drwxr-xr-x    2 ftp      ftp         65536 Dec 08 16:41 ru01-20140217T1244
    drwxr-xr-x    2 ftp      ftp         36864 Jan 15 16:07 ru05-20150105T1600
    drwxr-xr-x    2 ftp      ftp         65536 Feb 02 13:41 ru05-20150115T1443

    226 Directory send OK.
```

New NetCDF files should be uploaded to the directory [created above](#deployment-creation).  For example, uploading files to the ru05-20150115T1443 deployment is done as follows:

```
    ftp> cd ru05-20150115T1443
    250 Directory successfully changed.
    ftp> lcd LOCAL_DIRECTORY
    Local directory now LOCAL_DIRECTORY
    ftp> mput *.nc
```

Please remember to use the [proper](ngdac-netcdf-file-format-version-2.html#file-naming-conventions) file naming convention.

The resulting deployment directory structure will look something like this:

```
    /ru05-20150115T1443
        profile1.nc
        profile2.nc
        profile3.nc
        ...
```

A generic [ftp script](https://github.com/ioos/ioosngdac/blob/master/util/ncFtp2ngdac.pl), written in [Perl](http://www.perl.org/) is contained in the repository and may be used to upload the files to the **NGDAC**.  The script requires the following Perl non-core modules:
 + [Readonly](http://search.cpan.org/~roode/Readonly-1.03/Readonly.pm)
 + [Net::FTP](http://search.cpan.org/~shay/libnet-1.25/Net/FTP.pm)

**You must specify your credentials in the $USER and $PASS variables contained in the script**.

## Dataset Status

Once one or more files have been successfully uploaded for the specified deployment, the [aggregation](/ioosngdac/ngdac-architecture.html#data-assembly-center-architecture) process begins.  As there are multiple file syncing and aggregation processes going on, it will take some time for the data access end points on both the [ERDDAP](https://gliders.ioos.us/erddap/tabledap/index.html) and [THREDDS](https://gliders.ioos.us/thredds/catalog.html) servers to be created and populated.  The end-to-end processing pathway **currently takes 1 - 2 hrs**.  We are actively working on ways to decrease this time frame.

We've built a [dataset status](https://gliders.ioos.us/status/) page to provide administrators and users with the ability to track datasets through the end-to-end process.  The [home page](https://gliders.ioos.us/status/) displays a list of all data sets for which either/both the [ERDDAP](https://gliders.ioos.us/erddap/tabledap/index.html) and [THREDDS](https://gliders.ioos.us/thredds/catalog.html) are not yet available.  Please check this page before emailing the DAC administrators regarding data set availability.

## Dataset Archiving

Once a glider deployment is **completed** the data provider has the option to archive the dataset with the [National Centers for Environmental Information](https://www.ncei.noaa.gov/) national ocean archive.  **It is the responsibility of the data provider to mark the deployment as completed before the NCEI archival process begins**.

Here's how to mark a deployment as complete and submit the dataset to NCEI:

1. Navigate to the [GliderDAC providers page](https://gliders.ioos.us/providers/) and login with your account credentials.

2.Once logged

![GliderDAC - Deployments page](/ioosngdac/DAC_providers_your_deployments.png)

2. Select the deployment of interest from the table of deployments by clicking on the deployment name.

4. Under the **Edit** section on the right side of the deployment page, you'll see checkboxes for **Completed** and **Submit to NCEI on Completion**. Select both checkboxes and click the **Submit** button.

![GliderDAC - Deployments page](/ioosngdac/DAC_complete_deployment.png)

Once submitted, the [IOOS GliderDAC compliance checker](https://compliance.ioos.us/index.html) is run to check for compliance with NCEI's authority tables for project, institution, platform, and instrument. The results of these checks will be emailed on completion. If any of these checks have failed, NCEI will not archive the deployment.

There are typically 2 reasons that a deployment fails an NCEI check.

1. The dataset needs to be fixed if there is indeed an error (this can be as simple as a typo). Check the tables to see if there is an existing entry that can be used instead.

**NOTE:** ERDDAP uses the metadata from the latest file in a deployment to create an aggregation. So data providers only need to fix metadata on the latest file for the changes to be reflected in ERDDAP.

2. The NCEI tables need to be updated to include your new project, institution, instruments, or platforms. If you feel this is the case please email [glider.dac.support@noaa.gov](mailto:glider.dac.support@noaa.gov?subject=NCEI%20Authority%20Tables) to initiate that process.


## NCEI Authority Tables
The [National Centers for Environmental Information](https://www.ncei.noaa.gov/) authority tables are available here:
[https://gliders.ioos.us/ncei_authority_tables/](https://gliders.ioos.us/ncei_authority_tables/).