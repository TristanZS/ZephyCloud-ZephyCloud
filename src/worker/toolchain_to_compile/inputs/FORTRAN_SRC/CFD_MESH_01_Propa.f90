!######################################################################
!# ©Zephy-Science 2013                                                #
!# GPL3 Licence                                                       #
!######################################################################
!# Topography Data Transfer                                           #
!######################################################################

PROGRAM     CFD_MESH_01_Propa
IMPLICIT    NONE

integer:: iinfile0,iinfile1,iinfile2,ioutfile,nzcst,nz,ipt,igrpt,ng,ngroups,i1,i2,linelen,npoints,nelem,iz,ichar1,ichar2
integer:: ncharinfile0,ncharinfile1,ncharinfile2,ncharoutfile,ncharlogfile,arg_size,arg_status,freq
real:: htop,zming,zmaxg,xpt,ypt,zpt,xptm1,yptm1,dist,zground,z2use,ratio,delta_h,avancement
real,dimension(:),pointer:: z,xg,yg,zg
character(len=5):: frac
character(len=1000):: line,newline
character(len=1000):: infile0,infile1,infile2,outfile,logfile
character(len=10000):: arg_content

CALL get_command_argument(1,arg_content,arg_size,arg_status)
ncharinfile0=arg_size
infile0(1:ncharinfile0)=arg_content(1:arg_size)

CALL get_command_argument(2,arg_content,arg_size,arg_status)
ncharinfile1=arg_size
infile1(1:ncharinfile1)=arg_content(1:arg_size)

CALL get_command_argument(3,arg_content,arg_size,arg_status)
ncharinfile2=arg_size
infile2(1:ncharinfile2)=arg_content(1:arg_size)

CALL get_command_argument(4,arg_content,arg_size,arg_status)
ncharoutfile=arg_size
outfile(1:ncharoutfile)=arg_content(1:arg_size)

CALL get_command_argument(5,arg_content,arg_size,arg_status)
ncharlogfile=arg_size
logfile(1:ncharlogfile)=arg_content(1:arg_size)

iinfile0=1
iinfile1=2
iinfile2=3
ioutfile=4

open(iinfile0,file=infile0(1:ncharinfile0),status='old',action='read')
read(iinfile0,*) htop
read(iinfile0,*) nzcst
read(iinfile0,*) nz
allocate(z(nz))
do ipt=1,nz
	read(iinfile0,*) z(ipt)
enddo
close(iinfile0)

ng=0
open(iinfile1,file=infile1(1:ncharinfile1),status='old',action='read')
do
    read(iinfile1,*,end=800)
    ng=ng+1
enddo
800 rewind(iinfile1)
allocate(xg(ng))
allocate(yg(ng))
allocate(zg(ng))

zming=1.e+8
zmaxg=0.
do ipt=1,ng
	read(iinfile1,*) xg(ipt),yg(ipt),zg(ipt)
	zming=amin1(zming,zg(ipt))
	zmaxg=amax1(zmaxg,zg(ipt))
enddo
close(iinfile1)

xptm1=0.0001
yptm1=0.0001

open(iinfile2,file=infile2(1:ncharinfile2),status='old',action='read')
open(ioutfile,file=outfile(1:ncharoutfile),status='replace',action='write')
read(iinfile2,'(a)') line ; write(ioutfile,'(a)') trim(line)
read(iinfile2,*) line,i1,i2 ; linelen=len_trim(line) ; write(ioutfile,'(a,1x,i0,1x,i0)') line(:linelen),i1,i2
read(iinfile2,'(a)') line ; write(ioutfile,'(a)') trim(line)
read(iinfile2,'(a)') line ; write(ioutfile,'(a)') trim(line)
read(iinfile2,*) ngroups ; write(ioutfile,'(i0)') ngroups
do ipt=1,ngroups
	read(iinfile2,*) i1,i2,line
	linelen=len_trim(line)
	write(ioutfile,'(i0,1x,i0,1x,a)') i1,i2,'"'//line(:linelen)//'"'
enddo
do ipt=1,2
	read(iinfile2,'(a)') line ; write(ioutfile,'(a)') trim(line)
enddo
read(iinfile2,*) npoints ; write(ioutfile,'(i0)') npoints

freq=nint(amax1(npoints/20.,100.))

do ipt=1,npoints
    if(modulo(ipt,freq).eq.0)then
        if(logfile(1:ncharlogfile).ne.'NONE')then
            avancement=float(ipt)/npoints
            open(1,file=logfile(1:ncharlogfile),status='old',action='read',err=900)
            read(1,'(a)',end=900,err=900) line
            close(1)
            ichar1= index(line,'<progress_frac>')+15
            ichar2= index(line,'</progress_frac>')
            write(frac,'(f5.3)') avancement
            newline=line(1:ichar1)//frac//line(ichar2:)
            open(2,file=logfile(1:ncharlogfile),status='old',action='write',err=900)
            write(2,'(a)') newline
            close(2)
900         continue
        endif
    endif
	read(iinfile2,*) i1,xpt,ypt,zpt
	dist=(xpt-xptm1)**2+(ypt-yptm1)**2
	if (dist.gt.1) then
		do igrpt=1,ng
			dist=(xpt-xg(igrpt))**2+(ypt-yg(igrpt))**2
			if (dist.lt.1.) then
				zground=zg(igrpt)
				exit
			endif
		enddo
	endif
	iz=zpt
	if (iz+1<nzcst) then
		z2use=zground+z(iz+1)
	elseif (iz+1==nz) then
		z2use=zming+z(iz+1)
	else
		ratio=(htop-(z(nzcst+1)+zground))/(htop-(z(nzcst+1)+zming))
		delta_h=z(iz+1)-z(nzcst+1)
		z2use=z(nzcst+1)+zground+ratio*delta_h
	endif
	write(ioutfile,'(i0,1x,f20.6,1x,f20.6,1x,f20.6)') i1,xpt,ypt,z2use
	xptm1=xpt
	yptm1=ypt
enddo
read(iinfile2,'(a)') line ; write(ioutfile,'(a)') trim(line)
read(iinfile2,'(a)') line ; write(ioutfile,'(a)') trim(line)
read(iinfile2,*) nelem ; write(ioutfile,'(i0)') nelem
do ipt=1,nelem+1
	read(iinfile2,'(a)') line ; write(ioutfile,'(a)') trim(line)
enddo

close(iinfile2)
close(ioutfile)

if(logfile(1:ncharlogfile).ne.'NONE')then
	avancement=1.
	open(1,file=logfile(1:ncharlogfile),status='old',action='read',err=902)
	read(1,'(a)',end=902,err=902) line
	close(1)
	ichar1= index(line,'<progress_frac>')+15
	ichar2= index(line,'</progress_frac>')
	write(frac,'(f5.3)') avancement
	newline=line(1:ichar1)//frac//line(ichar2:)
	open(2,file=logfile(1:ncharlogfile),status='old',action='write',err=902)
	write(2,'(a)') newline
	close(2)
902 continue
endif

END PROGRAM CFD_MESH_01_Propa
