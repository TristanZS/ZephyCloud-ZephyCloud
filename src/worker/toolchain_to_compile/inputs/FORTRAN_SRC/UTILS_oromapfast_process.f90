!######################################################################
!# ©Zephy-Science 2013                                                #
!# GPL3 Licence                                                       #
!######################################################################
!# Elevation Data Evaluation from MAP files (fast version)            #
!######################################################################

PROGRAM     UTILS_oromap_process
IMPLICIT    NONE

integer:: iptsfile,imapfile,ioutfile,nval,npts
integer:: ipt,idir,imap,ichar1,ichar2,freq
integer:: ncharptsfile,ncharmapfile,ncharoutfile,ncharlogfile,arg_size,arg_status
real:: dmin,dx,dy,dist,rap,sumpond,zground,pond,epsilon,avancement,rnval,pi,none
real,dimension(9):: tabtan
real,dimension(12):: dist_dir,z_dir
real,dimension(:),pointer:: i1,i2,i3
real,dimension(:,:),pointer:: pts_xyz
character(len=3):: format
character(len=5):: frac
character(len=1000):: ptsfile,mapfile,outfile,logfile
character(len=1000):: line,newline
character(len=10000):: arg_content

CALL get_command_argument(1,arg_content,arg_size,arg_status)
ncharptsfile=arg_size
ptsfile(1:ncharptsfile)=arg_content(1:arg_size)

CALL get_command_argument(2,arg_content,arg_size,arg_status)
ncharmapfile=arg_size
mapfile(1:ncharmapfile)=arg_content(1:arg_size)

CALL get_command_argument(3,arg_content,arg_size,arg_status)
ncharoutfile=arg_size
outfile(1:ncharoutfile)=arg_content(1:arg_size)

CALL get_command_argument(4,arg_content,arg_size,arg_status)
ncharlogfile=arg_size
logfile(1:ncharlogfile)=arg_content(1:arg_size)

epsilon    =1.e-8
pi         =3.141592654
dmin       =1.e20
iptsfile   =1
imapfile   =2
ioutfile   =3
npts       =0

do idir=1,8
    tabtan(idir)=tan(idir*10.*pi/180.)
enddo
tabtan(9)=1.e+10

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

if (mapfile(ncharmapfile-1:ncharmapfile).ne.'_a')then

    open(imapfile,file=mapfile(1:ncharmapfile)//'.info',form='formatted',status='old',action='read')
    read(imapfile,*) format
    read(imapfile,*) nval
    close(imapfile)

    allocate(i1(nval)) ; allocate(i2(nval)) ; allocate(i3(nval))

    open(imapfile,file=mapfile(1:ncharmapfile),form='unformatted',status='old',action='read')
    read(imapfile) i1 ; read(imapfile) i2 ; read(imapfile) i3
    close(imapfile)

else

    open(imapfile,file=mapfile(1:ncharmapfile),status='old',action='read')
    read(imapfile,*) format ; read(imapfile,*) rnval ; nval=int(rnval)
    allocate(i1(nval)) ; allocate(i2(nval)) ; allocate(i3(nval))
    do imap=1,nval
        read(imapfile,*) i1(imap),i2(imap),i3(imap)
    enddo
    close(imapfile)

endif


open(ioutfile,file=outfile(1:ncharoutfile),status='replace',action='write')

avancement=0.
freq=nint(amax1(npts/20.,100.))

do ipt=1,npts

    if(modulo(ipt,freq).eq.0)then
        if(logfile(1:ncharlogfile).ne.'NONE')then
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

    dmin=1.e25
    do idir=1,12
        z_dir(idir)=0
        dist_dir(idir)=dmin
    enddo

    do imap=1,nval

        dx=i1(imap)-pts_xyz(ipt,1)
        dy=i2(imap)-pts_xyz(ipt,2)
        dist=dx*dx+dy*dy

        if (dist.lt.1.)then

            do idir=1,12
                z_dir(idir)=i3(imap)
                dist_dir(idir)=dist
            enddo
            EXIT

        else if(dist.lt.1000*dmin)then

            if(dx.eq.0.) dx=0.01
            rap=abs(dy/dx)
            idir=1
            do while((rap.ge.tabtan(idir)).and.(idir.lt.4))
                idir=idir+1
            enddo
            if ((dy.ge.0).and.(dx.le.0.))  then
                idir=idir+4
            else if ((dy.le.0.).and.(dx.le.0.)) then
                idir=idir+6
            else if ((dy.le.0.).and.(dx.ge.0.)) then
                idir=idir+9
            endif

            if(dist.lt.dist_dir(idir))then
                z_dir(idir)=i3(imap)
                dist_dir(idir)=dist
                dmin=min(dist,dmin)
            endif


        endif

    enddo

    sumpond=0.
    zground=0.
    do idir=1,12
         if  (z_dir(idir).le.1e+4)   then
             pond=1/sqrt(dist_dir(idir)+epsilon)
             zground=zground+pond*z_dir(idir)
             sumpond=sumpond+pond
         endif
    enddo
    pts_xyz(ipt,3)=anint(100.0*zground/sumpond)/100.0
    write(ioutfile,*) pts_xyz(ipt,1),pts_xyz(ipt,2),pts_xyz(ipt,3)

enddo

close(ioutfile)

avancement=1.
open(1,file=logfile(1:ncharlogfile),status='old',action='read',err=901)
read(1,'(a)',end=901,err=901) line
close(1)
ichar1= index(line,'<progress_frac>')+15
ichar2= index(line,'</progress_frac>')
write(frac,'(f5.3)') avancement
newline=line(1:ichar1)//frac//line(ichar2:)
open(2,file=logfile(1:ncharlogfile),status='old',action='write',err=901)
write(2,'(a)') newline
close(2)
901 continue

END PROGRAM UTILS_oromap_process
