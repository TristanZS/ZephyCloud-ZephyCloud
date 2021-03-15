!######################################################################
!# ©Zephy-Science 2013                                                #
!# GPL3 Licence                                                       #
!######################################################################
!# Roughness Data Evaluation                                          #
!######################################################################

PROGRAM     UTILS_rou_process
IMPLICIT    NONE

integer:: iptsfile,ifacfile,imapfile,ioutfile,nval,npts,ipt,ifac,imap,ichar1,ichar2,i1,i2,i3,nfac
integer:: ncharptsfile,ncharfacfile,ncharmapfile,ncharoutfile,ncharlogfile,arg_size,arg_status
integer ,dimension(:,:),pointer:: fac_123
real:: avancement,x1,x2,y1,y2,x3,y3,xp,yp,rough,dx,dy,dist,dmin,rnval,bidon
real,dimension(:),pointer:: m1,m2,m3
real,dimension(:,:),pointer:: pts_xy
character(len=3) :: format
character(len=5) :: frac
character(len=200) :: ptsfile,facfile,mapfile,outfile,logfile,arg_content
character(len=1000):: line,newline

CALL get_command_argument(1,arg_content,arg_size,arg_status)
ncharptsfile = arg_size
ptsfile(1:ncharptsfile) = arg_content(1:arg_size)

CALL get_command_argument(2,arg_content,arg_size,arg_status)
ncharfacfile = arg_size
facfile(1:ncharfacfile) = arg_content(1:arg_size)

CALL get_command_argument(3,arg_content,arg_size,arg_status)
ncharmapfile = arg_size
mapfile(1:ncharmapfile) = arg_content(1:arg_size)

CALL get_command_argument(4,arg_content,arg_size,arg_status)
ncharoutfile = arg_size
outfile(1:ncharoutfile) = arg_content(1:arg_size)

CALL get_command_argument(5,arg_content,arg_size,arg_status)
ncharlogfile = arg_size
logfile(1:ncharlogfile) = arg_content(1:arg_size)

iptsfile = 1
ifacfile = 2
imapfile = 3
ioutfile = 4
npts     = 0
nfac     = 0


open(iptsfile,file=ptsfile(1:ncharptsfile),status='old',action='read')
if (ptsfile(ncharptsfile-4:ncharptsfile).eq.'.msh2')then
    do ipt=1,8
        read(iptsfile,*)
    enddo
    read(iptsfile,*) npts
    ALLOCATE(pts_xy(npts,3))
    do ipt = 1,npts
        read(iptsfile,*) bidon,pts_xy(ipt,1),pts_xy(ipt,2)
    enddo
else
    do
        read(iptsfile,*,end=661) ; npts = npts + 1
    enddo
    661 ALLOCATE(pts_xy(npts,2))
    rewind(iptsfile)
    do ipt = 1,npts
        read(iptsfile,*) pts_xy(ipt,1),pts_xy(ipt,2)
    enddo
endif
close(iptsfile)

open(ifacfile,file=facfile(1:ncharfacfile),status='old',action='read')
do
    read(ifacfile,*,end=662) ; nfac = nfac + 1
enddo
662 ALLOCATE(fac_123(nfac,3))
rewind(ifacfile)
do ifac = 1,nfac
    read(ifacfile,*) fac_123(ifac,1),fac_123(ifac,2),fac_123(ifac,3)
enddo
close(ifacfile)

if (mapfile(ncharmapfile-1:ncharmapfile).ne.'_a')then

    open(imapfile,file=mapfile(1:ncharmapfile)//'.info',form='formatted',status='old',action='read')
    read(imapfile,*) format
    read(imapfile,*) nval
    close(imapfile)

    allocate(m1(nval)) ; allocate(m2(nval)) ; allocate(m3(nval))

    open(imapfile,file=mapfile(1:ncharmapfile),form='unformatted',status='old',action='read')
    read(imapfile) m1 ; read(imapfile) m2 ; read(imapfile) m3
    close(imapfile)

else

    open(imapfile,file=mapfile(1:ncharmapfile),status='old',action='read')
    read(imapfile,*) format ; read(imapfile,*) rnval ; nval=int(rnval)
    allocate(m1(nval)) ; allocate(m2(nval)) ; allocate(m3(nval))
    do imap=1,nval
        read(imapfile,*) m1(imap),m2(imap),m3(imap)
    enddo
    close(imapfile)

endif

open(ioutfile,file=outfile(1:ncharoutfile),status='replace',action='write')

avancement = 0.

do ifac = 1,nfac

    if(logfile(1:ncharlogfile).ne.'NONE')then

        if(modulo(ifac,25).eq.0)then
            avancement=float(ifac)/nfac
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

    i1 = fac_123(ifac,1) ; i2 = fac_123(ifac,2) ; i3 = fac_123(ifac,3)
    x1 = pts_xy(i1,1) ; x2 = pts_xy(i2,1) ; x3 = pts_xy(i3,1)
    y1 = pts_xy(i1,2) ; y2 = pts_xy(i2,2) ; y3 = pts_xy(i3,2)
    xp = (x1+x2+x3)/3. ; yp = (y1+y2+y3)/3.
    dmin  = +1.e20 ; rough = -999.
    do imap = 1,nval
        dx = m1(imap)-xp ; dy = m2(imap)-yp
        dist = dx*dx + dy*dy
        if(dist.lt.dmin)then
            dmin = dist ; rough = m3(imap)
        endif
    enddo
    write(ioutfile,*) i1-1,i2-1,i3-1,rough
enddo

close(ioutfile)

if(logfile(1:ncharlogfile).ne.'NONE')then
	avancement=1.
	open(1,file=logfile(1:ncharlogfile),status='old',action='read',err=900)
	read(1,'(a)',end=902,err=902) line
	close(1)
	ichar1= index(line,'<progress_frac>')+15
	ichar2= index(line,'</progress_frac>')
	write(frac,'(f5.3)') avancement
	newline=line(1:ichar1)//frac//line(ichar2:)
	open(2,file=logfile(1:ncharlogfile),status='old',action='write',err=900)
	write(2,'(a)') newline
	close(2)
902 continue
endif

END PROGRAM UTILS_rou_process
