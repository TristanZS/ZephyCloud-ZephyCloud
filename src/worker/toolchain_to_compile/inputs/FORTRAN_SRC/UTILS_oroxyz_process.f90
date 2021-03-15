!######################################################################
!# ©Zephy-Science 2013                                                #
!# GPL3 Licence                                                       #
!######################################################################
!# Elevation Data Evaluation from XYZ files                           #
!######################################################################

PROGRAM     UTILS_oroxyz_process
IMPLICIT    NONE

integer:: iptsfile,ixyzfile,ioutfile,nval,npts
integer:: ipt,idir,ixyz,ichar1,ichar2
integer:: ncharptsfile,ncharxyzfile,ncharoutfile,ncharlogfile,arg_size,arg_status
integer:: n,ioro,freq
real:: dmin,dx,dy,dist,rap,sumpond,zground,pond,epsilon,avancement,rnval,pi,none
real:: d,d1,d2,d3,d4,z1,z2,z3,z4
real,dimension(:),pointer:: i1,i2,i3
real,dimension(:,:),pointer:: pts_xyz
character(len=3):: format
character(len=5):: frac
character(len=1000):: ptsfile,xyzfile,outfile,logfile
character(len=1000):: line,newline
character(len=10000):: arg_content

CALL get_command_argument(1,arg_content,arg_size,arg_status)
ncharptsfile=arg_size
ptsfile(1:ncharptsfile)=arg_content(1:arg_size)

CALL get_command_argument(2,arg_content,arg_size,arg_status)
ncharxyzfile=arg_size
xyzfile(1:ncharxyzfile)=arg_content(1:arg_size)

CALL get_command_argument(3,arg_content,arg_size,arg_status)
ncharoutfile=arg_size
outfile(1:ncharoutfile)=arg_content(1:arg_size)

CALL get_command_argument(4,arg_content,arg_size,arg_status)
ncharlogfile=arg_size
logfile(1:ncharlogfile)=arg_content(1:arg_size)

n=2

iptsfile=121
ixyzfile=122
ioutfile=123

open(iptsfile,file=ptsfile(1:ncharptsfile),status='old',action='read')
if (ptsfile(ncharptsfile-4:ncharptsfile).eq.'.msh2')then
    do ipt=1,8
        read(iptsfile,*)
    enddo
    read(iptsfile,*) npts
    ALLOCATE(pts_xyz(npts,3))
    do ipt=1,npts
        read(iptsfile,*) none,pts_xyz(ipt,1),pts_xyz(ipt,2)
    enddo
else
    do
        read(iptsfile,*,end=660)
        npts=npts+1
    enddo
    660 rewind(iptsfile)
    ALLOCATE(pts_xyz(npts,3))
    do ipt=1,npts
        read(iptsfile,*) pts_xyz(ipt,1),pts_xyz(ipt,2)
    enddo
endif
close(iptsfile)

pts_xyz(:,3)=0.

if (xyzfile(ncharxyzfile-1:ncharxyzfile).ne.'_a')then

    open(ixyzfile,file=xyzfile(1:ncharxyzfile)//'.info',form='formatted',status='old',action='read')
    read(ixyzfile,*) format
    read(ixyzfile,*) nval
    close(ixyzfile)

    allocate(i1(nval)) ; allocate(i2(nval)) ; allocate(i3(nval))

    open(ixyzfile,file=xyzfile(1:ncharxyzfile),form='unformatted',status='old',action='read')
    read(ixyzfile) i1 ; read(ixyzfile) i2 ; read(ixyzfile) i3
    close(ixyzfile)

else

    open(ixyzfile,file=xyzfile(1:ncharxyzfile),status='old',action='read')
    read(ixyzfile,*) format ; read(ixyzfile,*) rnval ; nval=int(rnval)
    allocate(i1(nval)) ; allocate(i2(nval)) ; allocate(i3(nval))
    do ipt=1,nval
        read(ixyzfile,*) i1(ipt),i2(ipt),i3(ipt)
    enddo
    close(ixyzfile)

endif

open(ioutfile,file=outfile(1:ncharoutfile),status='replace',action='write')

avancement=0.

if (npts.gt.200)then
    freq=nint(amin1(npts/20.,100.))
else
    freq=5
endif

do ipt=1,npts

    if(logfile(1:ncharlogfile).ne.'NONE')then

        if(modulo(ipt,freq).eq.0)then
            avancement=float(ipt)/npts
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

    d1=1.e+8
    d2=1.e+8
    d3=1e+8
    d4=1e+8
    z1=-999.
    z2=-999.
    z3=-999.
    z4=-999.

    do ioro=1,nval
        d=sqrt((pts_xyz(ipt,1)-i1(ioro))**2+(pts_xyz(ipt,2)-i2(ioro))**2)
        if(d<d1)then
            d4=d3
            z4=z3
            d3=d2
            z3=z2
            d2=d1
            z2=z1
            d1=d
            z1=i3(ioro)
         elseif(d<d2)then
            d4=d3
            z4=z3
            d3=d2
            z3=z2
            d2=d
            z2=i3(ioro)
         elseif(d<d3)then
            d4=d3
            z4=z3
            d3=d
            z3=i3(ioro)
         elseif(d<d4)then
            d4=d
            z4=i3(ioro)
         endif
    enddo
    if(d1.le.0.01)then
        pts_xyz(ipt,3)=z1
    else
        pts_xyz(ipt,3)=(z1/(d1**n)+z2/(d2**n)+z3/(d3**n)+z4/(d4**n))/(1/(d1**n)+1/(d2**n)+1/(d3**n)+1/(d4**n))
    endif

    write(ioutfile,*) pts_xyz(ipt,1),pts_xyz(ipt,2),pts_xyz(ipt,3)

enddo

close(ioutfile)

avancement=1.
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
901 continue

END PROGRAM UTILS_oroxyz_process

